"""登录：单一站点密码（APP_PASSWORD）。设了才启用全站登录门（见 main.py 中间件）。"""
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import (
    APP_PASSWORD, auth_enabled, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter()


class LoginInput(BaseModel):
    password: str


@router.get("/status", tags=["Authentication"])
def auth_status():
    """前端据此判断是否需要登录。"""
    return {"auth_required": auth_enabled()}


@router.post("/login", tags=["Authentication"])
def login(body: LoginInput):
    # 未启用登录门（本地开发）：直接发 token，前端无障碍使用
    if not auth_enabled():
        token = create_access_token({"sub": "local"}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        return {"access_token": token, "token_type": "bearer"}

    if body.password != APP_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

    token = create_access_token({"sub": "admin"}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}
