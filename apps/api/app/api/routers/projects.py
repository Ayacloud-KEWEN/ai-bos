"""执行项目接口（Module 1）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from pydantic import BaseModel

from app.core.database import get_db
from app.models.project import Project, Playbook
from app.models.company import Company

router = APIRouter()


def _progress(pb: Playbook) -> int:
    steps = pb.steps or []
    if not steps:
        return 0
    done = sum(1 for s in steps if s.get("status") == "done")
    return round(done / len(steps) * 100)


def _pb_card(pb: Playbook) -> dict:
    return {"id": pb.id, "title": pb.title, "goal": pb.goal, "category": pb.category,
            "status": pb.status, "progress": _progress(pb), "steps_count": len(pb.steps or [])}


class ProjectInput(BaseModel):
    name: str
    objective: str | None = None
    company_id: str | None = None
    kpis: list[str] | None = None
    status: str | None = None


@router.post("", tags=["Projects"])
async def create_project(body: ProjectInput, db: AsyncSession = Depends(get_db)):
    p = Project(name=body.name, objective=body.objective, company_id=body.company_id, kpis=body.kpis or [])
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": p.id}


@router.get("", tags=["Projects"])
async def list_projects(db: AsyncSession = Depends(get_db)):
    projects = (await db.execute(select(Project).order_by(Project.created_at.desc()))).scalars().all()
    pbs = (await db.execute(select(Playbook))).scalars().all()
    by_proj: dict[str, list] = {}
    for pb in pbs:
        by_proj.setdefault(pb.project_id, []).append(pb)
    out = []
    for p in projects:
        ppbs = by_proj.get(p.id, [])
        progresses = [_progress(x) for x in ppbs] or [0]
        out.append({
            "id": p.id, "name": p.name, "objective": p.objective, "company_id": p.company_id,
            "status": p.status, "playbooks_count": len(ppbs),
            "progress": round(sum(progresses) / len(progresses)),
        })
    return out


@router.get("/{project_id}", tags=["Projects"])
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    company_name = None
    if p.company_id:
        c = (await db.execute(select(Company).where(Company.id == p.company_id))).scalar_one_or_none()
        company_name = c.name if c else None
    pbs = (await db.execute(
        select(Playbook).where(Playbook.project_id == project_id).order_by(Playbook.created_at.desc())
    )).scalars().all()
    return {
        "id": p.id, "name": p.name, "objective": p.objective, "company_id": p.company_id,
        "company_name": company_name, "status": p.status, "kpis": p.kpis or [],
        "playbooks": [_pb_card(pb) for pb in pbs],
    }


@router.patch("/{project_id}", tags=["Projects"])
async def update_project(project_id: str, body: ProjectInput, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.name is not None: p.name = body.name
    if body.objective is not None: p.objective = body.objective
    if body.company_id is not None: p.company_id = body.company_id
    if body.status is not None: p.status = body.status
    if body.kpis is not None: p.kpis = body.kpis
    await db.commit()
    return {"msg": "updated"}


@router.delete("/{project_id}", tags=["Projects"])
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(sa_delete(Playbook).where(Playbook.project_id == project_id))
    await db.execute(sa_delete(Project).where(Project.id == project_id))
    await db.commit()
    return {"msg": "deleted"}
