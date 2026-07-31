from __future__ import annotations

from fastapi import APIRouter

from apps.api.app.api.v1.endpoints import auth, admin

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(admin.router)