"""持续监控：复查联网建档公司的最新披露，发现变动生成告警。"""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.company import Company
from app.services.sources import registry
from app.services.alerts import create_alert

router = APIRouter()


@router.post("/run", tags=["Monitoring"])
async def run_monitoring(db: AsyncSession = Depends(get_db)):
    """对所有有数据源的公司复查最新披露；marker 变化则生成"新披露"告警。
    （手动触发；可由定时任务调用。本地 Ollama 环境无内置调度器。）"""
    companies = (await db.execute(
        select(Company).where(Company.source.isnot(None), Company.source != "upload")
    )).scalars().all()

    checked, new_alerts = 0, 0
    for c in companies:
        conn = registry.get_connector(c.source)
        if not conn or not c.source_external_id:
            continue
        try:
            marker = await asyncio.to_thread(conn.latest_marker, c.source_external_id)
        except Exception as e:
            print(f"[monitor] {c.id} failed: {e}")
            continue
        checked += 1
        c.last_monitored_at = datetime.now(timezone.utc)
        if marker and marker != c.monitor_marker:
            first_time = c.monitor_marker is None
            c.monitor_marker = marker
            if not first_time:  # 首次仅记录基线，不告警
                await create_alert(db, c.id, c.name, "disclosure",
                    "检测到新披露 / New disclosure",
                    f"{conn.label}: {marker}", severity="warning")
                new_alerts += 1
    await db.commit()
    return {"checked": checked, "new_alerts": new_alerts, "monitored_companies": len(companies)}
