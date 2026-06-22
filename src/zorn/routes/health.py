from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..backend_metadata import backend_mode, compatibility_metadata, enabled_surfaces
from ..config import AppSettings
from ..dependencies import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz(settings: Annotated[AppSettings, Depends(get_settings)]) -> dict[str, object]:
    return {
        "ok": True,
        "productName": settings.product_name,
        "compatibilityTarget": settings.compatibility_target,
    }
####


@router.get("/healthz/details")
def healthz_details(settings: Annotated[AppSettings, Depends(get_settings)]) -> dict[str, object]:
    return {
        "schemaVersion": "zorn.health.details.v1",
        "ok": True,
        "productName": settings.product_name,
        "compatibilityTarget": settings.compatibility_target,
        "backendMode": backend_mode(settings),
        "authMode": settings.auth_mode,
        "enabledSurfaces": enabled_surfaces(settings),
        "compatibility": compatibility_metadata(settings),
    }
####
