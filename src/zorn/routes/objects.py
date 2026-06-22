from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from ..compat import object_metadata_headers, object_metadata_wire, ttl_header_to_seconds
from ..dependencies import get_object_store, require_auth
from ..stores import ObjectStore

router = APIRouter(prefix="/objects", tags=["objects"], dependencies=[Depends(require_auth)])


@router.get("")
def list_objects(
    store: Annotated[ObjectStore, Depends(get_object_store)],
    prefix: Annotated[str | None, Query()] = None,
    since_timestamp: Annotated[str | None, Query(alias="sinceTimestamp")] = None,
    page_token: Annotated[str | None, Query(alias="pageToken")] = None,
    all_objects_in_mesh: Annotated[bool, Query(alias="allObjectsInMesh")] = False,
    max_page_size: Annotated[int | None, Query(alias="maxPageSize", ge=1, le=1000)] = None,
    limit: Annotated[int | None, Query(ge=1, le=1000)] = None,
) -> dict[str, Any]:
    _ = since_timestamp, page_token, all_objects_in_mesh
    resolved_limit = max_page_size or limit or 100
    objects = store.list(prefix=prefix, limit=resolved_limit)
    path_metadatas = [object_metadata_wire(metadata) for metadata in objects]
    return {"path_metadatas": path_metadatas, "next_page_token": None, "objects": objects}
####


@router.post("/{object_path:path}")
async def upload_object(
    object_path: str,
    request: Request,
    store: Annotated[ObjectStore, Depends(get_object_store)],
    content_type: Annotated[str | None, Header()] = None,
    time_to_live: Annotated[str | None, Header(alias="Time-To-Live")] = None,
    distribution_mode: Annotated[str | None, Header(alias="Distribution-Mode")] = None,
) -> dict[str, Any]:
    _ = distribution_mode
    body = await request.body()
    try:
        metadata = store.put(
            object_path=object_path,
            content=body,
            content_type=content_type or "application/octet-stream",
            ttl_seconds=ttl_header_to_seconds(time_to_live),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ####
    return object_metadata_wire(metadata)
####


@router.get("/{object_path:path}")
def get_object(
    object_path: str,
    store: Annotated[ObjectStore, Depends(get_object_store)],
) -> Response:
    try:
        result = store.get(object_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ####
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="object not found")
    ####
    metadata, body = result
    return Response(content=body, media_type=metadata["contentType"], headers=object_metadata_headers(metadata))
####


@router.head("/{object_path:path}")
def head_object(
    object_path: str,
    store: Annotated[ObjectStore, Depends(get_object_store)],
) -> Response:
    try:
        metadata = store.metadata(object_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ####
    if metadata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="object not found")
    ####
    return Response(content=b"", headers=object_metadata_headers(metadata))
####


@router.delete("/{object_path:path}")
def delete_object(
    object_path: str,
    store: Annotated[ObjectStore, Depends(get_object_store)],
) -> dict[str, Any]:
    try:
        deleted = store.delete(object_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ####
    return {"deleted": deleted, "objectPath": object_path}
####
