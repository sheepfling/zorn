from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ..backend_metadata import compatibility_metadata, enabled_surfaces
from ..config import AppSettings
from ..dependencies import get_settings, require_auth

router = APIRouter(prefix="/backend", tags=["backend"], dependencies=[Depends(require_auth)])


@router.get("/capabilities")
def backend_capabilities(settings: Annotated[AppSettings, Depends(get_settings)]) -> dict[str, Any]:
    metadata = compatibility_metadata(settings)
    return {
        "schemaVersion": "zorn.backend.capabilities.v1",
        "productName": settings.product_name,
        "surfaces": enabled_surfaces(settings),
        "supported": metadata["supported"],
        "partiallySupported": metadata["partiallySupported"],
        "unsupported": metadata["unsupported"],
    }
####


@router.get("/compatibility")
def backend_compatibility(settings: Annotated[AppSettings, Depends(get_settings)]) -> dict[str, Any]:
    return compatibility_metadata(settings)
####
