from __future__ import annotations

from typing import Any

import httpx


def main() -> None:
    base_url = "http://127.0.0.1:8080/api/v1"
    headers = {"Authorization": "Bearer dev-token"}
    entity = {"entityId": "smoke-entity", "isLive": True, "description": "contract smoke"}
    put_response = httpx.put(f"{base_url}/entities", json=entity, headers=headers, timeout=10.0)
    put_response.raise_for_status()

    poll_response = httpx.post(f"{base_url}/entities/events", json={"sessionToken": "0"}, headers=headers, timeout=10.0)
    poll_response.raise_for_status()
    poll_payload: dict[str, Any] = poll_response.json()
    assert "sessionToken" in poll_payload
    assert poll_payload["entityEvents"]

    object_response = httpx.post(
        f"{base_url}/objects/smoke/object.bin",
        content=b"hello",
        headers={**headers, "Content-Type": "application/octet-stream"},
        timeout=10.0,
    )
    object_response.raise_for_status()
    object_payload: dict[str, Any] = object_response.json()
    assert object_payload["content_identifier"]["path"] == "smoke/object.bin"

    task_response = httpx.post(
        f"{base_url}/tasks",
        json={"taskId": "smoke-task", "relations": {"assignee": {"system": {"entityId": "smoke-entity"}}}},
        headers=headers,
        timeout=10.0,
    )
    task_response.raise_for_status()
    assert task_response.status_code == 201

    listen_response = httpx.post(f"{base_url}/agent/listen", json={"entityId": "smoke-entity"}, headers=headers, timeout=10.0)
    listen_response.raise_for_status()
    assert "executeRequest" in listen_response.json()

    print("contract smoke passed")
####


if __name__ == "__main__":
    main()
####
