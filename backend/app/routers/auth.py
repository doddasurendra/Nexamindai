"""Registration, login, profile and admin user listing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut, UserUpdate
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower().strip()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    count = (await db.execute(select(func.count(User.id)))).scalar_one()
    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        role="admin" if count == 0 else "user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = (await db.execute(select(User).where(User.email == payload.email.lower().strip()))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return TokenResponse(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UserOut:
    if payload.name is not None:
        user.name = payload.name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/users", response_model=list[UserOut])
async def list_users(_: User = Depends(require_admin), db: AsyncSession = Depends(get_db)) -> list[UserOut]:
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    return [UserOut.model_validate(u) for u in users]
