"""应用设置接口：大模型 Provider 选择与配置（运行时可切换）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.services import llm

router = APIRouter()


async def _get_or_create(db: AsyncSession) -> AppSetting:
    row = (await db.execute(select(AppSetting).where(AppSetting.id == 1))).scalar_one_or_none()
    if not row:
        row = AppSetting(id=1, llm_provider="ollama", llm_providers_config={})
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def load_settings_into_runtime(db: AsyncSession):
    """启动时调用：把持久化的模型配置载入到 llm 运行时状态。
    并从环境变量播种（首次部署便利）：DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY /
    QWEN_API_KEY 填对应 provider 的 key；AIBOS_DEFAULT_PROVIDER 设默认 provider（仅当 DB 未改过）。"""
    import os
    row = await _get_or_create(db)
    llm.load_state(row.llm_provider, row.llm_providers_config or {})

    for env_key, provider in [("DEEPSEEK_API_KEY", "deepseek"), ("OPENAI_API_KEY", "openai"),
                              ("ANTHROPIC_API_KEY", "anthropic"), ("QWEN_API_KEY", "qwen")]:
        val = os.environ.get(env_key)
        if val:
            try:
                llm.update_provider_config(provider, api_key=val)
            except Exception:
                pass
    default = os.environ.get("AIBOS_DEFAULT_PROVIDER")
    if default and row.llm_provider == "ollama":  # DB 仍是默认，尚未手动改过 → 用 env 默认
        try:
            llm.set_provider(default)
        except Exception:
            pass


class ProviderConfigInput(BaseModel):
    provider: str
    model: str | None = None
    api_key: str | None = None


class ModelSettingsInput(BaseModel):
    active_provider: str | None = None          # 切换当前 provider
    config: ProviderConfigInput | None = None    # 更新某个 provider 的 model / api_key


@router.get("/model", tags=["Settings"])
async def get_model_settings():
    """返回 provider 列表与当前选择（不含明文 API Key）。"""
    return llm.public_info()


@router.put("/model", tags=["Settings"])
async def update_model_settings(body: ModelSettingsInput, db: AsyncSession = Depends(get_db)):
    try:
        if body.config:
            llm.update_provider_config(body.config.provider, body.config.model, body.config.api_key)
        if body.active_provider:
            llm.set_provider(body.active_provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 持久化
    row = await _get_or_create(db)
    state = llm.export_state()
    row.llm_provider = state["provider"]
    row.llm_providers_config = state["providers"]
    await db.commit()
    return llm.public_info()
