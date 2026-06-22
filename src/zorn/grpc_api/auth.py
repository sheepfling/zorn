from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import grpc

from ..config import AppSettings


PUBLIC_GRPC_METHOD_PREFIXES: tuple[str, ...] = (
    "/grpc.health.v1.Health/",
    "/grpc.reflection.v1alpha.ServerReflection/",
)


def token_is_allowed(settings: AppSettings, token: str | None) -> bool:
    if settings.auth_mode == "none":
        return True
    ####
    return bool(token and token in settings.static_tokens)
####


def bearer_token_from_metadata(metadata: tuple[tuple[str, str], ...]) -> str | None:
    for key, value in metadata:
        normalized_key = key.lower()
        if normalized_key == "authorization" and value.lower().startswith("bearer "):
            return value.split(" ", 1)[1].strip()
        ####
        if normalized_key == "x-api-key":
            return value.strip()
        ####
    ####
    return None
####


class AuthInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
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
        if self.settings.auth_mode == "none" or _is_public_method(handler_call_details.method):
            return handler
        ####
        token = bearer_token_from_metadata(tuple(handler_call_details.invocation_metadata or ()))
        if token_is_allowed(self.settings, token):
            return handler
        ####
        return _wrap_unauthenticated(handler)
    ####
####


def _is_public_method(method: str | None) -> bool:
    return any((method or "").startswith(prefix) for prefix in PUBLIC_GRPC_METHOD_PREFIXES)
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
