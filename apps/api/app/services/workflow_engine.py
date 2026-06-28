"""工作流引擎：用 LangGraph 把可视化节点图编译成可执行 DAG，自动编排运行各分析节点。
每个节点映射到现有的情报分析能力，针对运行所绑定的公司执行，并逐节点回写状态。
"""
import json
import asyncio
import operator
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from sqlalchemy import select, text as sql_text
from langgraph.graph import StateGraph, START, END

from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.models.document import CompanyDocument

# ---- 节点类型元数据（供前端调色板 + 分发） ----
NODE_TYPES = [
    {"type": "input", "label": "Company Input", "terminal": False},
    {"type": "financial", "label": "Financial Analysis"},
    {"type": "competitive", "label": "Competitive Analysis"},
    {"type": "due_diligence", "label": "Due Diligence"},
    {"type": "strategy", "label": "Strategy"},
    {"type": "sales", "label": "Sales Intelligence"},
    {"type": "market", "label": "Market Research"},
    {"type": "briefing", "label": "CEO Briefing"},
    {"type": "playbook", "label": "Generate Playbook"},
    {"type": "report", "label": "Report"},
]


async def _company_context(company_id: str) -> str:
    """从公司已存文档构建分析上下文（财务/竞争/尽调节点用）。"""
    from app.api.routers.chat import _load_any
    from app.services.analyzer import build_context_from_text
    async with AsyncSessionLocal() as db:
        docs = (await db.execute(
            select(CompanyDocument).where(CompanyDocument.company_id == company_id)
        )).scalars().all()
    texts = []
    for d in docs:
        try:
            texts.append(await asyncio.to_thread(_load_any, d.stored_path))
        except Exception:
            pass
    return await build_context_from_text("\n\n".join(texts))


async def _company_name(company_id: str) -> str:
    async with AsyncSessionLocal() as db:
        c = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
        return c.name if c else company_id


# ---- 节点处理器：返回一句话摘要 ----
async def _run_node(node_type: str, company_id: str, config: dict) -> str:
    from app.services import analyzer
    from app.api.routers.financials import persist_financials
    from app.api.routers.competitive import persist_competitive
    from app.api.routers.due_diligence import persist_due_diligence

    if node_type in ("input", "report", "company_scanner"):
        return "ok"

    if node_type == "financial":
        ctx = await _company_context(company_id)
        fin = await analyzer.analyze_financials(ctx)
        async with AsyncSessionLocal() as db:
            await persist_financials(db, company_id, fin, currency=fin.get("currency", "USD")); await db.commit()
        return f"{len(fin.get('periods', []))} periods"
    if node_type == "competitive":
        ctx = await _company_context(company_id)
        comp = await analyzer.analyze_competition(ctx, await _company_name(company_id))
        async with AsyncSessionLocal() as db:
            await persist_competitive(db, company_id, comp); await db.commit()
        return f"{len(comp.get('competitors', []))} competitors"
    if node_type == "due_diligence":
        ctx = await _company_context(company_id)
        dd = await analyzer.analyze_due_diligence(ctx)
        async with AsyncSessionLocal() as db:
            await persist_due_diligence(db, company_id, dd); await db.commit()
        return f"score {dd.get('overall_score')}"
    if node_type == "strategy":
        from app.api.routers.strategy import build_and_store_strategy
        await build_and_store_strategy(company_id); return "strategy ready"
    if node_type == "sales":
        from app.api.routers.sales_market import build_and_store_sales
        await build_and_store_sales(company_id); return "sales ready"
    if node_type == "market":
        from app.api.routers.sales_market import build_and_store_market
        await build_and_store_market(company_id); return "market ready"
    if node_type == "briefing":
        from app.api.routers.briefing import build_and_store_briefing
        await build_and_store_briefing(company_id); return "briefing ready"
    if node_type == "playbook":
        import uuid
        from app.models.project import Playbook
        from app.api.routers.playbooks import _build_playbook
        goal = (config or {}).get("goal") or "Growth & execution"
        pb_id = f"pb_{uuid.uuid4().hex[:8]}"
        async with AsyncSessionLocal() as db:
            db.add(Playbook(id=pb_id, company_id=company_id, title=goal, goal=goal, status="Generating", steps=[]))
            await db.commit()
        await _build_playbook(pb_id, company_id, goal)
        return f"playbook {pb_id}"
    return "skipped"


async def _set_node_state(run_id: str, node_id: str, patch: dict):
    """用 jsonb_set 原子更新单个节点状态，避免并发分支互相覆盖。"""
    async with AsyncSessionLocal() as db:
        await db.execute(sql_text(
            "UPDATE workflow_runs SET node_states = jsonb_set(coalesce(node_states,'{}'::jsonb), "
            "ARRAY[:nid], :val::jsonb) WHERE id = :rid"
        ), {"nid": node_id, "val": json.dumps(patch), "rid": run_id})
        await db.commit()


class _WState(TypedDict):
    logs: Annotated[list, operator.add]


def _make_handler(run_id: str, company_id: str, node: dict):
    nid, ntype, config = node["id"], node.get("type", "input"), node.get("config") or {}

    async def _handler(state):
        await _set_node_state(run_id, nid, {"status": "running"})
        try:
            summary = await _run_node(ntype, company_id, config)
            await _set_node_state(run_id, nid, {"status": "done", "summary": summary})
            return {"logs": [f"{nid} ({ntype}) done: {summary}"]}
        except Exception as e:
            await _set_node_state(run_id, nid, {"status": "failed", "error": str(e)[:200]})
            return {"logs": [f"{nid} ({ntype}) FAILED: {e}"]}

    return _handler


async def run_workflow(run_id: str, nodes: list, edges: list, company_id: str):
    """编译并执行工作流（LangGraph）。"""
    try:
        node_ids = {n["id"] for n in nodes}
        g = StateGraph(_WState)
        for n in nodes:
            g.add_node(n["id"], _make_handler(run_id, company_id, n))

        targets, sources = set(), set()
        for e in edges:
            if e["source"] in node_ids and e["target"] in node_ids:
                g.add_edge(e["source"], e["target"])
                sources.add(e["source"]); targets.add(e["target"])
        roots = [nid for nid in node_ids if nid not in targets]
        leaves = [nid for nid in node_ids if nid not in sources]
        for r in roots:
            g.add_edge(START, r)
        for l in leaves:
            g.add_edge(l, END)

        compiled = g.compile()
        result = await compiled.ainvoke({"logs": []})
        logs = result.get("logs", [])
        failed = any("FAILED" in x for x in logs)
        async with AsyncSessionLocal() as db:
            await db.execute(sql_text(
                "UPDATE workflow_runs SET status=:s, logs=:l, completed_at=:t WHERE id=:rid"
            ), {"s": "failed" if failed else "completed", "l": json.dumps(logs),
                "t": datetime.now(timezone.utc), "rid": run_id})
            await db.commit()
    except Exception as e:
        print(f"[workflow] run {run_id} crashed: {e}")
        async with AsyncSessionLocal() as db:
            await db.execute(sql_text(
                "UPDATE workflow_runs SET status='failed', logs=:l, completed_at=:t WHERE id=:rid"
            ), {"l": json.dumps([f"engine error: {e}"]), "t": datetime.now(timezone.utc), "rid": run_id})
            await db.commit()
