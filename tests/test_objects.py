from __future__ import annotations

from fastapi.testclient import TestClient


def test_upload_get_head_list_and_delete_object(client: TestClient) -> None:
    content = b"mock object bytes"
    upload_response = client.post(
        "/api/v1/objects/reports/example.bin",
        content=content,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["objectPath"] == "reports/example.bin"

    get_response = client.get("/api/v1/objects/reports/example.bin")
    assert get_response.status_code == 200
    assert get_response.content == content
    assert get_response.headers["x-checksum-sha256"]

    head_response = client.head("/api/v1/objects/reports/example.bin")
    assert head_response.status_code == 200
    assert head_response.headers["content-length"] == str(len(content))

    list_response = client.get("/api/v1/objects", params={"prefix": "reports"})
    assert list_response.status_code == 200
    assert list_response.json()["objects"][0]["objectPath"] == "reports/example.bin"

    delete_response = client.delete("/api/v1/objects/reports/example.bin")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
####
