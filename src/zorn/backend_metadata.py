from __future__ import annotations

from typing import Any

from .config import AppSettings


STREAM_GUARANTEES: dict[str, Any] = {
    "ordering": "monotonic database event sequence per Zorn instance",
    "entity_event_types": ["CREATE", "UPDATE", "DELETED"],
    "task_event_types": ["CREATE", "UPDATE", "CANCELED"],
    "preexisting_controls": {
        "entities": ["preExistingOnly"],
        "tasks": ["includePreexisting", "excludePreexistingTasks"],
    },
    "heartbeat": {
        "config": "C2_COMPAT_HEARTBEAT_SECONDS",
        "minimum_seconds": 0.001,
    },
}


def backend_mode(settings: AppSettings) -> str:
    if settings.database_url == "sqlite:///:memory:":
        return "sqlite-memory"
    ####
    if settings.database_url.startswith("sqlite"):
        return "sqlite"
    ####
    return "sqlalchemy"
####


def enabled_surfaces(settings: AppSettings) -> dict[str, Any]:
    return {
        "rest": {
            "entities": True,
            "tasks": True,
            "objects": True,
            "oauth_dev": settings.auth_mode == "oauth-dev",
            "verification": True,
            "backend_metadata": True,
        },
        "grpc": {
            "entities": True,
            "tasks": True,
            "objects": False,
            "reflection": True,
            "health": True,
            "tls_mode": settings.grpc_tls_mode,
        },
    }
####


def compatibility_metadata(settings: AppSettings) -> dict[str, Any]:
    return {
        "schemaVersion": "zorn.backend.compatibility.v1",
        "productName": settings.product_name,
        "compatibilityTarget": settings.compatibility_target,
        "backendMode": backend_mode(settings),
        "auth": {
            "mode": settings.auth_mode,
            "staticTokenCount": len(settings.static_tokens),
            "supportsBearerToken": settings.auth_mode in {"static", "oauth-dev"},
            "supportsApiKey": settings.auth_mode in {"static", "oauth-dev"},
        },
        "surfaces": enabled_surfaces(settings),
        "streamGuarantees": STREAM_GUARANTEES,
        "supported": [
            "entities.publish",
            "entities.get",
            "entities.delete_tombstone",
            "entities.events.poll",
            "entities.events.snapshot",
            "entities.stream_sse",
            "tasks.create",
            "tasks.get",
            "tasks.query",
            "tasks.update_status",
            "tasks.cancel",
            "tasks.listen_as_agent",
            "tasks.stream_sse",
            "tasks.events.snapshot",
            "objects.upload",
            "objects.download",
            "objects.head",
            "objects.list",
            "objects.delete",
            "verification.state",
        ],
        "partiallySupported": [
            "grpc.entities",
            "grpc.tasks",
            "auth.oauth_dev",
            "entity.schema_normalization",
        ],
        "unsupported": [
            "objects.grpc",
            "mesh.distribution",
            "production_oauth_refresh",
            "hla_adapter",
            "tak_adapter",
        ],
        "mockShortcuts": [
            "single_node_sqlite_backend",
            "local_dev_auth_tokens",
            "object_mesh_distribution_not_simulated",
            "manual_control_frames_heartbeat_only",
        ],
    }
####
