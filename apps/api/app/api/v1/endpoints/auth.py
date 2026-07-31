from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.auth.deps import get_current_user, get_valid_session
from apps.api.app.auth.router import router
from apps.api.app.auth.service.authentication import login, logout, refresh, register
from apps.api.app.auth.service.authorization import get_user_permissions, get_user_roles
from apps.api.app.auth.service.session import (
    get_session_by_id,
    list_user_sessions,
    revoke_all_other_sessions,
    revoke_session,
)
from apps.api.app.auth.service.verification import (
    create_email_verification_token,
    create_password_reset_token,
    reset_password,
    verify_email,
)
from apps.api.app.db.session import get_session as get_db
from apps.api.app.models.session import Session as SessionModel
from apps.api.app.models.user import User
from apps.api.app.schemas.models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SessionListResponse,
    SessionResponse,
    UpdateProfileRequest,
    UserProfileResponse,
    UserResponse,
    VerifyEmailRequest,
)


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_endpoint(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    user, access_token, refresh_token_str, expires_in = await register(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
        db=db,
    )

    response = RegisterResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )
    response._access_token = access_token
    response._refresh_token = refresh_token_str
    response._expires_in = expires_in
    return response


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    user, session, access_token, refresh_token_str, expires_in = await login(
        email=body.email,
        password=body.password,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
        device_info=body.device_info,
        db=db,
    )

    roles = await get_user_roles(user.id, db)
    permissions = await get_user_permissions(user.id, db)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=expires_in,
        session_id=session.id,
        user=UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            is_verified=user.is_verified,
            is_active=user.is_active,
            locale=user.locale,
            roles=roles,
            permissions=permissions,
            created_at=user.created_at,
        ),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_endpoint(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    new_token_string, access_token, expires_in = await refresh(
        refresh_token_string=body.refresh_token,
        db=db,
    )

    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_token_string,
        expires_in=expires_in,
    )


@router.post("/logout", status_code=204)
async def logout_endpoint(
    body: LogoutRequest,
    user: User = Depends(get_current_user),
    session: SessionModel = Depends(get_valid_session),
    db: AsyncSession = Depends(get_db),
) -> None:
    await logout(
        user_id=user.id,
        session_id=session.id,
        refresh_token_string=body.refresh_token,
        all_sessions=body.all_sessions,
        db=db,
    )
    return None


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    roles = await get_user_roles(user.id, db)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        locale=user.locale,
        roles=roles,
        created_at=user.created_at,
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.locale is not None:
        user.locale = body.locale
    await db.flush()
    await db.refresh(user)

    roles = await get_user_roles(user.id, db)
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        locale=user.locale,
        roles=roles,
        created_at=user.created_at,
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user: User = Depends(get_current_user),
    current_session: SessionModel = Depends(get_valid_session),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    sessions = await list_user_sessions(user.id, db)
    active_count = sum(1 for s in sessions if s.is_active)
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                device_info=s.device_info,
                is_active=s.is_active,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
                current=s.id == current_session.id,
            )
            for s in sessions
        ],
        total=len(sessions),
        active_count=active_count,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    current_session: SessionModel = Depends(get_valid_session),
    db: AsyncSession = Depends(get_db),
) -> None:
    from uuid import UUID
    from apps.api.app.core.exceptions import NotFoundError

    sid = UUID(session_id)
    session = await get_session_by_id(sid, user.id, db)
    if session is None:
        raise NotFoundError("Session not found")
    await revoke_session(sid, db)
    return None


@router.delete("/sessions", status_code=200)
async def delete_other_sessions(
    user: User = Depends(get_current_user),
    session: SessionModel = Depends(get_valid_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await revoke_all_other_sessions(user.id, session.id, db)
    return {"revoked_count": count}


@router.post("/verify-email")
async def verify_email_endpoint(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await verify_email(body.token, db)
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and not user.is_verified:
        token = await create_email_verification_token(user.id, db)

    return {"message": "If account exists, verification email sent"}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and user.password_hash is not None:
        token = await create_password_reset_token(user.id, db)

    return {"message": "If an account exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password_endpoint(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await reset_password(
        token_string=body.token,
        new_password=body.new_password,
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", ""),
        db=db,
    )
    return {"message": "Password has been reset"}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from apps.api.app.auth.service.password import hash_password, verify_password
    from apps.api.app.auth.service.verification import _check_password_history
    from apps.api.app.models.password_history import PasswordHistory

    if not verify_password(body.current_password, user.password_hash or ""):
        from apps.api.app.core.exceptions import ValidationError
        raise ValidationError("Current password is incorrect")

    from apps.api.app.auth.service.password import validate_and_hash
    new_hash = await validate_and_hash(body.new_password, str(user.id))

    from sqlalchemy import select
    history_result = await db.execute(
        select(PasswordHistory.password_hash)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(5)
    )
    for historical_hash in history_result.scalars().all():
        if verify_password(body.new_password, historical_hash):
            raise ValidationError("Password has been used recently")

    user.password_hash = new_hash
    db.add(PasswordHistory(user_id=user.id, password_hash=new_hash))
    await db.flush()

    return {"message": "Password changed successfully"}