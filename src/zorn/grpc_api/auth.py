from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import grpc

from ..config import AppSettings
from ..oauth_dev import OAuthDevTokenStore


def token_is_allowed(settings: AppSettings, token_store: OAuthDevTokenStore, token: str | None) -> bool:
    if settings.auth_mode == "none":
        return True
    ####
    if not token:
        return False
    ####
    return token in settings.static_tokens or (settings.auth_mode == "oauth-dev" and token_store.is_valid(token))
####


def bearer_token_from_metadata(metadata: tuple[tuple[str, str], ...]) -> str | None:
    for key, value in metadata:
        normalized_key = key.lower()
        if normalized_key in {"authorization", "anduril-sandbox-authorization"} and value.lower().startswith("bearer "):
            return value.split(" ", 1)[1].strip()
        ####
        if normalized_key == "x-api-key":
            return value.strip()
        ####
    ####
    return None
####


def has_required_sandbox_metadata(metadata: tuple[tuple[str, str], ...]) -> bool:
    for key, value in metadata:
        normalized_key = key.lower()
        if normalized_key in {"x-anduril-sandbox", "anduril-sandbox-authorization"} and value.strip():
            return True
        ####
    ####
    return False
####


class AuthInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, settings: AppSettings, token_store: OAuthDevTokenStore) -> None:
        self.settings = settings
        self.token_store = token_store
    ####

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler | None]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        handler = await continuation(handler_call_details)
        if handler is None:
            return None
        ####
        if self.settings.auth_mode == "none":
            return handler
        ####
        metadata = tuple(handler_call_details.invocation_metadata or ())
        if self.settings.require_sandbox_header and not has_required_sandbox_metadata(metadata):
            return _wrap_permission_denied(handler, "Missing sandbox header")
        ####
        token = bearer_token_from_metadata(metadata)
        if token_is_allowed(self.settings, self.token_store, token):
            return handler
        ####
        return _wrap_unauthenticated(handler)
    ####
####

def _wrap_unauthenticated(handler: grpc.RpcMethodHandler) -> grpc.RpcMethodHandler:
    async def abort_unary_unary(request: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing bearer token")
        raise AssertionError("unreachable after gRPC abort")
    ####

    async def abort_unary_stream(request: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing bearer token")
        raise AssertionError("unreachable after gRPC abort")
        yield None
    ####

    async def abort_stream_unary(request_iterator: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing bearer token")
        raise AssertionError("unreachable after gRPC abort")
    ####

    async def abort_stream_stream(request_iterator: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing bearer token")
        raise AssertionError("unreachable after gRPC abort")
        yield None
    ####

    if handler.request_streaming and handler.response_streaming:
        return grpc.stream_stream_rpc_method_handler(
            abort_stream_stream,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    ####
    if handler.request_streaming:
        return grpc.stream_unary_rpc_method_handler(
            abort_stream_unary,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    ####
    if handler.response_streaming:
        return grpc.unary_stream_rpc_method_handler(
            abort_unary_stream,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    ####
    return grpc.unary_unary_rpc_method_handler(
        abort_unary_unary,
        request_deserializer=handler.request_deserializer,
        response_serializer=handler.response_serializer,
    )
####


def _wrap_permission_denied(handler: grpc.RpcMethodHandler, detail: str) -> grpc.RpcMethodHandler:
    async def abort_unary_unary(request: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.PERMISSION_DENIED, detail)
        raise AssertionError("unreachable after gRPC abort")
    ####

    async def abort_unary_stream(request: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.PERMISSION_DENIED, detail)
        raise AssertionError("unreachable after gRPC abort")
        yield None
    ####

    async def abort_stream_unary(request_iterator: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.PERMISSION_DENIED, detail)
        raise AssertionError("unreachable after gRPC abort")
    ####

    async def abort_stream_stream(request_iterator: Any, context: grpc.aio.ServicerContext) -> Any:
        await context.abort(grpc.StatusCode.PERMISSION_DENIED, detail)
        raise AssertionError("unreachable after gRPC abort")
        yield None
    ####

    if handler.request_streaming and handler.response_streaming:
        return grpc.stream_stream_rpc_method_handler(
            abort_stream_stream,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    ####
    if handler.request_streaming:
        return grpc.stream_unary_rpc_method_handler(
            abort_stream_unary,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    ####
    if handler.response_streaming:
        return grpc.unary_stream_rpc_method_handler(
            abort_unary_stream,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
    ####
    return grpc.unary_unary_rpc_method_handler(
        abort_unary_unary,
        request_deserializer=handler.request_deserializer,
        response_serializer=handler.response_serializer,
    )
####
