from __future__ import annotations

from fastapi import FastAPI

from .config import AppSettings, load_settings
from .routes import entities, health, oauth, objects, tasks
from .runtime import build_store_bundle


def build_app(settings: AppSettings | None = None) -> FastAPI:
    bundle = build_store_bundle(settings or load_settings())
    resolved_settings = bundle.settings

    app = FastAPI(
        title=resolved_settings.product_name,
        description=f"Configurable local C2/COP compatibility sandbox for {resolved_settings.compatibility_target}.",
        version="0.1.0",
    )
    app.state.settings = resolved_settings
    app.state.database = bundle.database
    app.state.entity_store = bundle.entity_store
    app.state.task_store = bundle.task_store
    app.state.object_store = bundle.object_store

    app.include_router(health.router)
    app.include_router(oauth.router, prefix=resolved_settings.api_prefix)
    app.include_router(entities.router, prefix=resolved_settings.api_prefix)
    app.include_router(tasks.router, prefix=resolved_settings.api_prefix)
    app.include_router(objects.router, prefix=resolved_settings.api_prefix)
    return app
####
