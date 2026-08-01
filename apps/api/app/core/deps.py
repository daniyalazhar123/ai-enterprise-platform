from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from apps.api.app.auth.deps import (
    get_current_user,
    get_valid_session,
    require_permission,
    require_role,
)
from apps.api.app.core.auth import get_current_user_optional
from apps.api.app.models.session import Session
from apps.api.app.models.user import User

CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
CurrentSession = Annotated[Session, Depends(get_valid_session)]
SessionDep = CurrentSession

__all__ = [
    "CurrentUser",
    "OptionalUser",
    "CurrentSession",
    "SessionDep",
    "require_permission",
    "require_role",
]
