from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Register ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    display_name: str = Field(..., min_length=2, max_length=255)


class RegisterResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_verified: bool
    created_at: datetime
    message: str = "Registration successful. Please verify your email."


# ── Login ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: dict | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    session_id: UUID
    user: "UserResponse"


# ── Refresh ─────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


# ── Logout ──────────────────────────────────────────────────────────────

class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_sessions: bool = False


# ── Change Password ────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)


# ── Forgot / Reset Password ────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=12, max_length=128)


# ── Email Verification ─────────────────────────────────────────────────

class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


# ── OAuth ──────────────────────────────────────────────────────────────

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str | None = None
    provider: str


class OAuthRedirectResponse(BaseModel):
    authorization_url: str


# ── User Responses ─────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    is_verified: bool
    is_active: bool
    locale: str
    roles: list[str] = []
    permissions: list[str] = []
    created_at: datetime


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    is_verified: bool
    locale: str
    roles: list[str]
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=255)
    avatar_url: str | None = None
    locale: str | None = Field(None, max_length=10)


# ── Session ────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    id: UUID
    ip_address: str
    user_agent: str
    device_info: dict
    is_active: bool
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool = False


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
    active_count: int


# ── Error ──────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    error_code: str
    details: dict | None = None
    request_id: str | None = None


# ── Token Introspection ────────────────────────────────────────────────

class TokenIntrospectResponse(BaseModel):
    active: bool
    sub: str | None = None
    sid: str | None = None
    email: str | None = None
    name: str | None = None
    roles: list[str] = []
    permissions: list[str] = []
    exp: int | None = None
    iat: int | None = None
    iss: str | None = None
    jti: str | None = None
    type: str | None = None


class TokenIntrospectRequest(BaseModel):
    token: str