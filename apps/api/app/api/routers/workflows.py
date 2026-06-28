"""工作流接口（Module 3）：可视化定义 + LangGraph 自动编排执行。"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from pydantic import BaseModel

from app.core.database import get_db
from app.models.workflow import Workflow, WorkflowRun
from app.models.company import Company
from app.services.workflow_engine import NODE_TYPES, run_workflow

router = APIRouter()


@router.get("/node-types", tags=["Workflows"])
async def node_types():
    return {"node_types": NODE_TYPES}


class WorkflowInput(BaseModel):
    name: str
    description: str | None = None
    nodes: list | None = None
    edges: list | None = None


@router.post("", tags=["Workflows"])
async def create_workflow(body: WorkflowInput, db: AsyncSession = Depends(get_db)):
    w = Workflow(name=body.name, description=body.description, nodes=body.nodes or [], edges=body.edges or [])
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return {"id": w.id}


@router.post("/template", tags=["Workflows"])
async def create_template(db: AsyncSession = Depends(get_db)):
    """创建一条完整情报流水线工作流：输入→财务→竞争→尽调→战略→销售→市场→简报→报告。"""
    chain = ["input", "financial", "competitive", "due_diligence", "strategy", "sales", "market", "briefing", "report"]
    nodes, edges = [], []
    for i, t in enumerate(chain):
        nid = f"n{i+1}"
        nodes.append({"id": nid, "type": t, "position": {"x": 80 + (i % 3) * 240, "y": 60 + (i // 3) * 150}, "config": {}})
        if i > 0:
            edges.append({"id": f"e{i}", "source": f"n{i}", "target": nid})
    w = Workflow(name="Full Intelligence Pipeline", description="情报全流程：从公司输入到执行报告",
                 nodes=nodes, edges=edges)
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return {"id": w.id}


@router.get("", tags=["Workflows"])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Workflow).order_by(Workflow.created_at.desc()))).scalars().all()
    return [{"id": w.id, "name": w.name, "description": w.description,
             "node_count": len(w.nodes or [])} for w in rows]


@router.get("/runs/{run_id}", tags=["Workflows"])
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"id": r.id, "workflow_id": r.workflow_id, "company_id": r.company_id,
            "status": r.status, "node_states": r.node_states or {}, "logs": r.logs or []}


@router.get("/{workflow_id}", tags=["Workflows"])
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    w = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"id": w.id, "name": w.name, "description": w.description,
            "nodes": w.nodes or [], "edges": w.edges or []}


@router.put("/{workflow_id}", tags=["Workflows"])
async def update_workflow(workflow_id: str, body: WorkflowInput, db: AsyncSession = Depends(get_db)):
    w = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if body.name is not None: w.name = body.name
    if body.description is not None: w.description = body.description
    if body.nodes is not None: w.nodes = body.nodes
    if body.edges is not None: w.edges = body.edges
    await db.commit()
    return {"msg": "saved"}


@router.delete("/{workflow_id}", tags=["Workflows"])
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(sa_delete(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id))
    await db.execute(sa_delete(Workflow).where(Workflow.id == workflow_id))
    await db.commit()
    return {"msg": "deleted"}


class RunInput(BaseModel):
    company_id: str


@router.post("/{workflow_id}/run", tags=["Workflows"])
async def run(workflow_id: str, body: RunInput, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    w = (await db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    company = (await db.execute(select(Company).where(Company.id == body.company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not w.nodes:
        raise HTTPException(status_code=400, detail="Workflow has no nodes")

    run_id = f"wr_{uuid.uuid4().hex[:10]}"
    node_states = {n["id"]: {"status": "pending"} for n in w.nodes}
    db.add(WorkflowRun(id=run_id, workflow_id=workflow_id, company_id=body.company_id,
                       status="running", node_states=node_states, logs=[]))
    await db.commit()
    background_tasks.add_task(run_workflow, run_id, w.nodes, w.edges or [], body.company_id)
    return {"run_id": run_id}


@router.get("/{workflow_id}/runs", tags=["Workflows"])
async def list_runs(workflow_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id).order_by(WorkflowRun.started_at.desc()).limit(10)
    )).scalars().all()
    return [{"id": r.id, "company_id": r.company_id, "status": r.status,
             "started_at": r.started_at.isoformat() if r.started_at else None} for r in rows]
