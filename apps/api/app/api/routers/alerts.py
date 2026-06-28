"""告警列表与已读管理。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.core.database import get_db
from app.models.alert import Alert

router = APIRouter()


@router.get("", tags=["Alerts"])
async def list_alerts(unread_only: bool = False, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if unread_only:
        q = q.where(Alert.is_read == False)  # noqa: E712
    rows = (await db.execute(q)).scalars().all()
    unread = (await db.execute(
        select(func.count()).select_from(Alert).where(Alert.is_read == False)  # noqa: E712
    )).scalar_one()
    return {
        "unread_count": unread,
        "alerts": [
            {"id": a.id, "company_id": a.company_id, "company_name": a.company_name,
             "type": a.type, "severity": a.severity, "title": a.title, "detail": a.detail,
             "is_read": a.is_read, "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in rows
        ],
    }


@router.patch("/{alert_id}/read", tags=["Alerts"])
async def mark_read(alert_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(update(Alert).where(Alert.id == alert_id).values(is_read=True))
    await db.commit()
    return {"msg": "ok"}


@router.post("/read-all", tags=["Alerts"])
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    await db.execute(update(Alert).where(Alert.is_read == False).values(is_read=True))  # noqa: E712
    await db.commit()
    return {"msg": "ok"}
