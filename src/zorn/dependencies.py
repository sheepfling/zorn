from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from .config import AppSettings
from .auth_scopes import required_scope_for_rest_path
from .oauth_dev import OAuthDevTokenStore
from .stores import EntityStore, ObjectStore, TaskStore


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings
####


def get_entity_store(request: Request) -> EntityStore:
    return request.app.state.entity_store
####


def get_task_store(request: Request) -> TaskStore:
    return request.app.state.task_store
####


def get_object_store(request: Request) -> ObjectStore:
    return request.app.state.object_store
####


def require_auth(
    request: Request,
    settings: Annotated[AppSettings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
    x_anduril_sandbox: Annotated[str | None, Header()] = None,
    anduril_sandbox_authorization: Annotated[str | None, Header()] = None,
) -> None:
    if settings.auth_mode == "none":
        return
    ####
    if settings.require_sandbox_header and not (x_anduril_sandbox or anduril_sandbox_authorization):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing sandbox header")
    ####
    if x_api_key and settings.auth_mode in {"static", "oauth-dev"} and x_api_key in settings.static_tokens:
        return
    ####
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    ####
    token = authorization.split(" ", 1)[1].strip()
    if settings.auth_mode in {"static", "oauth-dev"} and token in settings.static_tokens:
        return
    ####
    oauth_dev_token_store: OAuthDevTokenStore = request.app.state.oauth_dev_token_store
    if settings.auth_mode == "oauth-dev" and oauth_dev_token_store.is_valid(token):
        if token not in settings.static_tokens:
            required_scope = required_scope_for_rest_path(str(request.url.path))
            if required_scope and not oauth_dev_token_store.token_scope_allows(token, required_scope):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient OAuth scope")
            ####
        ####
        return
    ####
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
####
