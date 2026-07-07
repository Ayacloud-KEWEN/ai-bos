"""认证：多用户（用户名/邮箱 + 密码，存 DB）+ 共享密码破窗登录。
登录门开关见 security.auth_enabled()；中间件在 main.py。"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.core.security import (
    APP_PASSWORD, auth_enabled, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    get_password_hash, verify_password, decode_token,
)

router = APIRouter()


class LoginInput(BaseModel):
    username: str | None = None
    password: str


@router.get("/status", tags=["Authentication"])
def auth_status():
    return {"auth_required": auth_enabled()}


@router.post("/login", tags=["Authentication"])
async def login(body: LoginInput, db: AsyncSession = Depends(get_db)):
    # 未启用登录门（本地开发）：直接发 token
    if not auth_enabled():
        return {"access_token": create_access_token({"sub": "local"}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
                "token_type": "bearer"}

    uname = (body.username or "").strip()
    # 1) 数据库用户（用户名=email 字段）
    if uname:
        user = (await db.execute(select(User).where(User.email == uname))).scalar_one_or_none()
        if user and user.is_active and verify_password(body.password, user.hashed_password):
            return {"access_token": create_access_token({"sub": uname}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
                    "token_type": "bearer"}
    # 2) 共享"破窗"密码（任意用户名）
    if APP_PASSWORD and body.password == APP_PASSWORD:
        return {"access_token": create_access_token({"sub": uname or "admin"}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
                "token_type": "bearer"}

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误 / Invalid credentials")


@router.get("/me", tags=["Authentication"])
async def me(request: Request):
    """返回当前登录用户名（从 token 解析）。未启用登录门时返回 local。"""
    if not auth_enabled():
        return {"username": "local", "auth_required": False}
    hdr = request.headers.get("Authorization", "")
    token = request.query_params.get("token") or (hdr[7:].strip() if hdr.startswith("Bearer ") else "")
    payload = decode_token(token) if token else None
    return {"username": payload.get("sub") if payload else None, "auth_required": True}


# ---- 用户管理（受登录门保护）----
class UserInput(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    is_superuser: bool | None = False


@router.get("/users", tags=["Authentication"])
async def list_users(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return [{"id": u.id, "username": u.email, "full_name": u.full_name,
             "is_superuser": u.is_superuser, "is_active": u.is_active} for u in rows]


@router.post("/users", tags=["Authentication"])
async def create_user(body: UserInput, db: AsyncSession = Depends(get_db)):
    uname = body.username.strip()
    if not uname or not body.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    exists = (await db.execute(select(User).where(User.email == uname))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="用户已存在 / User exists")
    u = User(email=uname, hashed_password=get_password_hash(body.password),
             full_name=body.full_name, is_superuser=bool(body.is_superuser))
    db.add(u)
    await db.commit()
    return {"id": u.id}


@router.delete("/users/{user_id}", tags=["Authentication"])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(sa_delete(User).where(User.id == user_id))
    await db.commit()
    return {"msg": "deleted"}
