from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


class ApiTestClientTransport:
    def __init__(self, client: TestClient) -> None:
        self.client = client
    ####

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self.client.request(
            method,
            path,
            json=json_payload,
            content=body,
            headers=headers,
        )
        assert response.status_code < 400, response.text
        if not response.content:
            return {}
        ####
        payload = response.json()
        return payload if isinstance(payload, dict) else {"value": payload}
    ####
####
