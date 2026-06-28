"""报告导出：把公司全维度情报渲染成可打印为 PDF 的 HTML 报告。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.intel import gather_intelligence
from app.services.report_html import render_report

router = APIRouter()


@router.get("/{company_id}/report", tags=["Report"], response_class=HTMLResponse)
async def company_report(company_id: str, db: AsyncSession = Depends(get_db)):
    intel = await gather_intelligence(db, company_id)
    if not intel:
        raise HTTPException(status_code=404, detail="Company not found")
    return HTMLResponse(content=render_report(intel))
