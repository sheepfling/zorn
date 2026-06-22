from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Request

from ..config import AppSettings

router = APIRouter(tags=["oauth"])


@router.post("/oauth/token")
async def get_token(request: Request) -> dict[str, Any]:
    settings: AppSettings = request.app.state.settings
    content_type = request.headers.get("content-type", "")
    scope: str | None = None
    if "application/json" in content_type:
        body = await request.json()
        scope = body.get("scope") if isinstance(body, dict) else None
    else:
        raw = (await request.body()).decode("utf-8")
        parsed = parse_qs(raw)
        scopes = parsed.get("scope") or []
        scope = scopes[0] if scopes else None
    ####
    if settings.auth_mode == "oauth-dev":
        issued = request.app.state.oauth_dev_token_store.issue_token(scope=scope)
        return {
            "access_token": issued.token,
            "token_type": "Bearer",
            "expires_in": issued.expires_in,
            "scope": issued.scope,
        }
    ####
    token = settings.static_tokens[0] if settings.static_tokens else "dev-token"
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": scope or "local-dev",
    }
####
