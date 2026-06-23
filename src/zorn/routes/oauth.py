from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, status

from ..config import AppSettings

router = APIRouter(tags=["oauth"])


@router.post("/oauth/token")
async def get_token(request: Request) -> dict[str, Any]:
    settings: AppSettings = request.app.state.settings
    content_type = request.headers.get("content-type", "")
    grant_type: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scope: str | None = None
    if "application/json" in content_type:
        body = await request.json()
        if isinstance(body, dict):
            grant_type = body.get("grant_type") if isinstance(body.get("grant_type"), str) else None
            client_id = body.get("client_id") if isinstance(body.get("client_id"), str) else None
            client_secret = body.get("client_secret") if isinstance(body.get("client_secret"), str) else None
            scope = body.get("scope") if isinstance(body.get("scope"), str) else None
    else:
        raw = (await request.body()).decode("utf-8")
        parsed = parse_qs(raw)
        grant_types = parsed.get("grant_type") or []
        grant_type = grant_types[0] if grant_types else None
        client_ids = parsed.get("client_id") or []
        client_id = client_ids[0] if client_ids else None
        client_secrets = parsed.get("client_secret") or []
        client_secret = client_secrets[0] if client_secrets else None
        scopes = parsed.get("scope") or []
        scope = scopes[0] if scopes else None
    ####
    if grant_type and grant_type != "client_credentials":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported OAuth grant_type.")
    ####
    if settings.auth_mode == "oauth-dev":
        if not client_id or not client_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="client_id and client_secret are required.")
        ####
        if settings.oauth_scope_mode == "locked" and scope:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested OAuth scope is not enabled in this startup profile.")
        ####
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
