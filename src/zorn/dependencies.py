from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from .config import AppSettings
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
    settings: Annotated[AppSettings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if settings.auth_mode == "none":
        return
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
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
####
