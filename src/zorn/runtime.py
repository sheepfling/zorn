from __future__ import annotations

from dataclasses import dataclass

from .config import AppSettings, load_settings
from .db import Database
from .stores import EntityStore, ObjectStore, TaskStore


@dataclass(frozen=True, slots=True)
class StoreBundle:
    settings: AppSettings
    database: Database
    entity_store: EntityStore
    task_store: TaskStore
    object_store: ObjectStore
####


def build_store_bundle(settings: AppSettings | None = None) -> StoreBundle:
    resolved_settings = settings or load_settings()
    database = Database(resolved_settings.database_url)
    database.create_schema()
    return StoreBundle(
        settings=resolved_settings,
        database=database,
        entity_store=EntityStore(
            database,
            allow_generated_ids=resolved_settings.allow_generated_entity_ids,
            enforce_source_update_time=resolved_settings.enforce_source_update_time,
        ),
        task_store=TaskStore(database),
        object_store=ObjectStore(
            database,
            root=resolved_settings.object_root,
            max_object_bytes=resolved_settings.max_object_bytes,
        ),
    )
####
