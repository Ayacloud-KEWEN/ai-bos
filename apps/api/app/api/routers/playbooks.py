"""Playbook 接口（Module 2）：从公司情报生成可执行方法论 + 步骤执行跟踪。"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from pydantic import BaseModel

from app.core.database import get_db, AsyncSessionLocal
from app.models.project import Playbook
from app.models.company import Company
from app.services.intel import gather_intelligence, intelligence_to_text
from app.services.analyzer import generate_playbook

router = APIRouter()


def _progress(steps) -> int:
    steps = steps or []
    if not steps:
        return 0
    return round(sum(1 for s in steps if s.get("status") == "done") / len(steps) * 100)


async def _build_playbook(playbook_id: str, company_id: str, goal: str):
    try:
        async with AsyncSessionLocal() as db:
            intel = await gather_intelligence(db, company_id)
        if not intel:
            raise ValueError("No company intelligence")
        pb = await generate_playbook(intelligence_to_text(intel), goal)
        steps = []
        for i, s in enumerate(pb.get("steps", []) or []):
            steps.append({
                "id": f"s{i+1}", "order": i + 1, "title": s.get("title", ""),
                "objective": s.get("objective", ""), "owner": s.get("owner", ""),
                "deliverable": s.get("deliverable", ""), "kpi": s.get("kpi", ""), "status": "todo",
            })
        async with AsyncSessionLocal() as db:
            row = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
            if not row:
                return
            row.title = pb.get("title") or row.title
            row.objective = pb.get("objective", "")
            row.category = pb.get("category", "")
            row.difficulty = pb.get("difficulty", "")
            row.estimated_time = pb.get("estimated_time", "")
            row.expected_outcome = pb.get("expected_outcome", "")
            row.language = pb.get("language", "en")
            row.steps = steps
            row.deliverables = pb.get("deliverables", [])
            row.kpis = pb.get("kpis", [])
            row.success_criteria = pb.get("success_criteria", [])
            row.status = "Ready"
            await db.commit()
        print(f"[playbook] generated {playbook_id}")
    except Exception as e:
        print(f"[playbook] generation failed {playbook_id}: {e}")
        async with AsyncSessionLocal() as db:
            row = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
            if row:
                row.status = "Failed"
                await db.commit()


class GenerateInput(BaseModel):
    company_id: str
    goal: str
    project_id: str | None = None


@router.post("/generate", tags=["Playbooks"])
async def generate(body: GenerateInput, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company).where(Company.id == body.company_id))).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    pb = Playbook(
        id=f"pb_{uuid.uuid4().hex[:8]}", project_id=body.project_id, company_id=body.company_id,
        title=body.goal or f"{company.name} Playbook", goal=body.goal, status="Generating", steps=[],
    )
    db.add(pb)
    await db.commit()
    background_tasks.add_task(_build_playbook, pb.id, body.company_id, body.goal)
    return {"playbook_id": pb.id, "status": "Generating"}


@router.get("", tags=["Playbooks"])
async def list_playbooks(project_id: str | None = None, company_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Playbook).order_by(Playbook.created_at.desc())
    if project_id:
        q = q.where(Playbook.project_id == project_id)
    if company_id:
        q = q.where(Playbook.company_id == company_id)
    rows = (await db.execute(q)).scalars().all()
    return [{"id": p.id, "title": p.title, "goal": p.goal, "status": p.status,
             "progress": _progress(p.steps), "company_id": p.company_id, "project_id": p.project_id}
            for p in rows]


@router.get("/{playbook_id}", tags=["Playbooks"])
async def get_playbook(playbook_id: str, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return {
        "id": p.id, "project_id": p.project_id, "company_id": p.company_id, "title": p.title,
        "goal": p.goal, "objective": p.objective, "category": p.category, "difficulty": p.difficulty,
        "estimated_time": p.estimated_time, "expected_outcome": p.expected_outcome, "status": p.status,
        "steps": p.steps or [], "deliverables": p.deliverables or [], "kpis": p.kpis or [],
        "success_criteria": p.success_criteria or [], "progress": _progress(p.steps),
    }


class StepStatusInput(BaseModel):
    status: str  # todo / doing / done


@router.patch("/{playbook_id}/steps/{step_id}", tags=["Playbooks"])
async def update_step(playbook_id: str, step_id: str, body: StepStatusInput, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Playbook not found")
    steps = [dict(s) for s in (p.steps or [])]  # 复制以触发 JSONB 变更
    found = False
    for s in steps:
        if s.get("id") == step_id:
            s["status"] = body.status
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Step not found")
    p.steps = steps
    await db.commit()
    return {"msg": "updated", "progress": _progress(steps)}


@router.delete("/{playbook_id}", tags=["Playbooks"])
async def delete_playbook(playbook_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(sa_delete(Playbook).where(Playbook.id == playbook_id))
    await db.commit()
    return {"msg": "deleted"}
