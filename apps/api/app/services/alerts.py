"""告警生成辅助。"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert


async def create_alert(db: AsyncSession, company_id: str | None, company_name: str,
                       type_: str, title: str, detail: str = "", severity: str = "info"):
    db.add(Alert(
        company_id=company_id, company_name=company_name, type=type_,
        title=title, detail=detail, severity=severity,
    ))
