from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from ..backend_metadata import compatibility_metadata
from ..config import AppSettings
from ..dependencies import get_entity_store, get_object_store, get_settings, get_task_store, require_auth
from ..events import event_snapshot
from ..stores import EntityStore, ObjectStore, TaskStore

router = APIRouter(prefix="/verification", tags=["verification"], dependencies=[Depends(require_auth)])


@router.get("/state")
def verification_state(
    settings: Annotated[AppSettings, Depends(get_settings)],
    entity_store: Annotated[EntityStore, Depends(get_entity_store)],
    task_store: Annotated[TaskStore, Depends(get_task_store)],
    object_store: Annotated[ObjectStore, Depends(get_object_store)],
) -> dict[str, Any]:
    return {
        "schemaVersion": "zorn.verification.state.v1",
        "backend": compatibility_metadata(settings),
        "entities": entity_store.list_all(),
        "tasks": task_store.query({}),
        "objects": object_store.list(limit=1000),
        "events": {
            "entities": event_snapshot(entity_store.database, stream="entity"),
            "tasks": event_snapshot(task_store.database, stream="task"),
            "objects": event_snapshot(object_store.database, stream="object"),
        },
    }
####
