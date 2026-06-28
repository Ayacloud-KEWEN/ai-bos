"""商学院（Module 7）：AI 商业模拟 + 场景目录。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.academy import Simulation
from app.services.analyzer import generate_sim_turn

router = APIRouter()

SCENARIOS = [
    {"key": "startup", "title": "从0到1创办初创公司", "track": "创业",
     "scenario": "你是一名创始人，刚拿到一笔小额天使投资，要把一个产品想法做成可持续的初创公司。"},
    {"key": "fundraising", "title": "完成一轮融资", "track": "融资",
     "scenario": "你是创始人/CFO，公司需要在 6 个月内完成一轮融资以支撑增长，面对投资人尽调与谈判。"},
    {"key": "market_entry", "title": "进入一个新市场", "track": "国际化",
     "scenario": "你负责把一家成长期公司带入一个全新的海外市场，需要做本地化、渠道与合规决策。"},
    {"key": "product_launch", "title": "发布一款新产品", "track": "产品",
     "scenario": "你是产品负责人，要在竞争激烈的市场里规划并发布一款新产品，平衡时间、质量与预算。"},
    {"key": "crisis", "title": "应对一次经营危机", "track": "领导力",
     "scenario": "你是 CEO，公司突遭重大危机（资金链/公关/关键客户流失之一），需要带团队化险为夷。"},
]


@router.get("/scenarios", tags=["Academy"])
async def scenarios():
    return {"scenarios": SCENARIOS}


def _history_text(history: list) -> str:
    lines = []
    for h in history or []:
        lines.append(f"情境：{h.get('situation','')[:200]}")
        lines.append(f"决策：{h.get('decision','')}")
        if h.get("outcome"):
            lines.append(f"结果：{h.get('outcome','')[:200]}")
    return "\n".join(lines)


def _view(s: Simulation) -> dict:
    return {
        "id": s.id, "scenario_key": s.scenario_key, "title": s.title, "track": s.track,
        "status": s.status, "round": s.round, "current": s.current or {},
        "history": s.history or [], "final_assessment": s.final_assessment,
    }


class StartInput(BaseModel):
    scenario_key: str


@router.post("/simulations", tags=["Academy"])
async def start(body: StartInput, db: AsyncSession = Depends(get_db)):
    sc = next((x for x in SCENARIOS if x["key"] == body.scenario_key), None)
    if not sc:
        raise HTTPException(status_code=404, detail="Scenario not found")
    turn = await generate_sim_turn(sc["scenario"], "", "(开始)", 1)
    s = Simulation(
        scenario_key=sc["key"], title=sc["title"], track=sc["track"], status="active", round=1,
        current={"situation": turn.get("situation", ""), "options": turn.get("options", [])},
        history=[],
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _view(s)


class ActInput(BaseModel):
    decision: str


@router.post("/simulations/{sim_id}/act", tags=["Academy"])
async def act(sim_id: str, body: ActInput, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Simulation).where(Simulation.id == sim_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if s.status != "active":
        raise HTTPException(status_code=400, detail="Simulation already completed")
    decision = (body.decision or "").strip()
    if not decision:
        raise HTTPException(status_code=400, detail="Empty decision")

    scenario = next((x["scenario"] for x in SCENARIOS if x["key"] == s.scenario_key), s.title or "")
    turn = await generate_sim_turn(scenario, _history_text(s.history), decision, (s.round or 1) + 1)

    history = list(s.history or [])
    cur = s.current or {}
    history.append({
        "situation": cur.get("situation", ""), "options": cur.get("options", []),
        "decision": decision, "outcome": turn.get("outcome", ""),
        "feedback": turn.get("feedback", ""), "score": turn.get("score", 0),
    })
    s.history = history
    s.round = (s.round or 1) + 1

    if turn.get("is_final") or s.round >= 7:
        s.status = "completed"
        s.final_assessment = {"summary": turn.get("final_assessment", ""),
                              "scores": turn.get("final_scores", {})}
        s.current = {"situation": turn.get("situation", ""), "options": []}
    else:
        s.current = {"situation": turn.get("situation", ""), "options": turn.get("options", [])}

    await db.commit()
    await db.refresh(s)
    return _view(s)


@router.get("/simulations", tags=["Academy"])
async def list_simulations(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Simulation).order_by(Simulation.created_at.desc()).limit(20))).scalars().all()
    return [{"id": s.id, "title": s.title, "track": s.track, "status": s.status, "round": s.round,
             "scenario_key": s.scenario_key} for s in rows]


@router.get("/simulations/{sim_id}", tags=["Academy"])
async def get_simulation(sim_id: str, db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(Simulation).where(Simulation.id == sim_id))).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return _view(s)
