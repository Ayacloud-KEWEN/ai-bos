"""业务资产生成器接口（Module 6）：投资备忘录/销售Deck/Battlecard/外联邮件下载。"""
import re
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.intel import gather_intelligence
from app.services import asset_builder

router = APIRouter()

_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _safe(name: str) -> str:
    ascii_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "company"
    return ascii_name


def _file_response(content: bytes | str, filename: str, media_type: str) -> Response:
    body = content.encode("utf-8") if isinstance(content, str) else content
    disp = f"attachment; filename=\"{_safe(filename)}\"; filename*=UTF-8''{quote(filename)}"
    return Response(content=body, media_type=media_type, headers={"Content-Disposition": disp})


async def _intel(db, company_id):
    intel = await gather_intelligence(db, company_id)
    if not intel:
        raise HTTPException(status_code=404, detail="Company not found")
    return intel


@router.get("/{company_id}/assets", tags=["Business Assets"])
async def list_assets(company_id: str, db: AsyncSession = Depends(get_db)):
    intel = await _intel(db, company_id)
    name = intel["company"]["name"]
    return {
        "company_id": company_id,
        "assets": [
            {"kind": "investor-memo", "label": "Investor Memo (Word)", "ext": "docx", "ready": bool(intel.get("briefing") or intel.get("financial"))},
            {"kind": "sales-deck", "label": "Sales Deck (PPT)", "ext": "pptx", "ready": bool(intel.get("sales") or intel.get("competitive") or intel.get("market"))},
            {"kind": "battlecard", "label": "Battlecard (Word)", "ext": "docx", "ready": bool(intel.get("competitive"))},
            {"kind": "outreach-email", "label": "Outreach Email (Text)", "ext": "txt", "ready": bool(intel.get("sales"))},
        ],
        "company_name": name,
    }


@router.get("/{company_id}/assets/investor-memo.docx", tags=["Business Assets"])
async def investor_memo(company_id: str, db: AsyncSession = Depends(get_db)):
    intel = await _intel(db, company_id)
    data = asset_builder.build_investor_memo(intel)
    return _file_response(data, f"{intel['company']['name']}-Investor-Memo.docx", _DOCX)


@router.get("/{company_id}/assets/sales-deck.pptx", tags=["Business Assets"])
async def sales_deck(company_id: str, db: AsyncSession = Depends(get_db)):
    intel = await _intel(db, company_id)
    data = asset_builder.build_sales_deck(intel)
    return _file_response(data, f"{intel['company']['name']}-Sales-Deck.pptx", _PPTX)


@router.get("/{company_id}/assets/battlecard.docx", tags=["Business Assets"])
async def battlecard(company_id: str, db: AsyncSession = Depends(get_db)):
    intel = await _intel(db, company_id)
    data = asset_builder.build_battlecard(intel)
    return _file_response(data, f"{intel['company']['name']}-Battlecard.docx", _DOCX)


@router.get("/{company_id}/assets/outreach-email.txt", tags=["Business Assets"])
async def outreach_email(company_id: str, db: AsyncSession = Depends(get_db)):
    intel = await _intel(db, company_id)
    text = asset_builder.build_outreach_email(intel)
    return _file_response(text, f"{intel['company']['name']}-Outreach-Email.txt", "text/plain; charset=utf-8")
