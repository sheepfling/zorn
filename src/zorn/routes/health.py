from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

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
