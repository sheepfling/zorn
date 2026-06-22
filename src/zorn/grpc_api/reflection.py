from __future__ import annotations

from collections.abc import Iterable

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.descriptor import FileDescriptor
import grpc
from typing import Any

from .proto_modules import LatticeProtoModules


REFLECTION_SERVICE_NAME = "grpc.reflection.v1alpha.ServerReflection"


def add_reflection_service(
    server: grpc.aio.Server,
    *,
    proto_modules: LatticeProtoModules,
    extra_service_names: Iterable[str] = (),
) -> None:
    service_names = (
        "anduril.entitymanager.v1.EntityManagerAPI",
        "anduril.taskmanager.v1.TaskManagerAPI",
        *extra_service_names,
        REFLECTION_SERVICE_NAME,
    )
    server.add_generic_rpc_handlers(
        (
            _ReflectionHandler(
                service_names=tuple(sorted(set(service_names))),
                root_files=(
                    proto_modules.entity_grpcapi.DESCRIPTOR,
                    proto_modules.task_grpcapi.DESCRIPTOR,
                ),
            ),
        )
    )
####


def _message_classes() -> tuple[Any, Any]:
    pool = descriptor_pool.Default()
    try:
        request_descriptor = pool.FindMessageTypeByName("grpc.reflection.v1alpha.ServerReflectionRequest")
        response_descriptor = pool.FindMessageTypeByName("grpc.reflection.v1alpha.ServerReflectionResponse")
    except KeyError:
        pool.Add(_reflection_file_descriptor())
        request_descriptor = pool.FindMessageTypeByName("grpc.reflection.v1alpha.ServerReflectionRequest")
        response_descriptor = pool.FindMessageTypeByName("grpc.reflection.v1alpha.ServerReflectionResponse")
    ####
    return (
        message_factory.GetMessageClass(request_descriptor),
        message_factory.GetMessageClass(response_descriptor),
    )
####


class _ReflectionHandler(grpc.GenericRpcHandler):
    def __init__(self, *, service_names: tuple[str, ...], root_files: tuple[FileDescriptor, ...]) -> None:
        self.service_names = service_names
        self.root_files = root_files
    ####

    def service(self, handler_call_details: grpc.HandlerCallDetails) -> grpc.RpcMethodHandler | None:
        if handler_call_details.method == "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo":
            request_type, response_type = _message_classes()
            return grpc.stream_stream_rpc_method_handler(
                self._server_reflection_info,
                request_deserializer=request_type.FromString,
                response_serializer=lambda response: response.SerializeToString(),
            )
        ####
        return None
    ####

    async def _server_reflection_info(self, request_iterator, context: grpc.aio.ServicerContext):
        async for request in request_iterator:
            yield self._response_for_request(request)
        ####
    ####

    def _response_for_request(self, request):
        _, response_type = _message_classes()
        response = response_type()
        response.valid_host = getattr(request, "host", "")
        response.original_request.CopyFrom(request)
        request_kind = request.WhichOneof("message_request")
        if request_kind == "list_services":
            services = response.list_services_response.service
            for service_name in self.service_names:
                services.add().name = service_name
            ####
            return response
        ####
        if request_kind == "file_containing_symbol":
            file_descriptor = _file_containing_symbol(request.file_containing_symbol, self.root_files)
            if file_descriptor is not None:
                _append_file_descriptors(response.file_descriptor_response.file_descriptor_proto, file_descriptor)
                return response
            ####
            return _error_response(response, 5, f"symbol not found: {request.file_containing_symbol}")
        ####
        if request_kind == "file_by_filename":
            try:
                file_descriptor = descriptor_pool.Default().FindFileByName(request.file_by_filename)
            except KeyError:
                return _error_response(response, 5, f"file not found: {request.file_by_filename}")
            ####
            _append_file_descriptors(response.file_descriptor_response.file_descriptor_proto, file_descriptor)
            return response
        ####
        return _error_response(response, 12, f"unsupported reflection request: {request_kind}")
    ####
####


def _file_containing_symbol(symbol: str, root_files: tuple[FileDescriptor, ...]) -> FileDescriptor | None:
    pool = descriptor_pool.Default()
    try:
        return pool.FindFileContainingSymbol(symbol)
    except KeyError:
        pass
    ####
    for file_descriptor in root_files:
        if any(service.full_name == symbol for service in file_descriptor.services_by_name.values()):
            return file_descriptor
        ####
    ####
    return None
####


def _append_file_descriptors(target, file_descriptor: FileDescriptor) -> None:
    seen: set[str] = set()

    def visit(current: FileDescriptor) -> None:
        if current.name in seen:
            return
        ####
        seen.add(current.name)
        for dependency in current.dependencies:
            visit(dependency)
        ####
        target.append(current.serialized_pb)
    ####

    visit(file_descriptor)
####


def _error_response(response, code: int, message: str):
    response.error_response.error_code = code
    response.error_response.error_message = message
    return response
####


def _reflection_file_descriptor() -> descriptor_pb2.FileDescriptorProto:
    descriptor = descriptor_pb2.FileDescriptorProto()
    descriptor.name = "grpc/reflection/v1alpha/reflection.proto"
    descriptor.package = "grpc.reflection.v1alpha"
    descriptor.syntax = "proto3"

    request = descriptor.message_type.add()
    request.name = "ServerReflectionRequest"
    _add_string_field(request, "host", 1)
    request.oneof_decl.add().name = "message_request"
    _add_string_field(request, "file_by_filename", 3, oneof_index=0)
    _add_string_field(request, "file_containing_symbol", 4, oneof_index=0)
    _add_string_field(request, "file_containing_extension", 5, oneof_index=0)
    _add_string_field(request, "all_extension_numbers_of_type", 6, oneof_index=0)
    _add_string_field(request, "list_services", 7, oneof_index=0)

    extension_request = descriptor.message_type.add()
    extension_request.name = "ExtensionRequest"
    _add_string_field(extension_request, "containing_type", 1)
    extension_number = extension_request.field.add()
    extension_number.name = "extension_number"
    extension_number.number = 2
    extension_number.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension_number.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32

    response = descriptor.message_type.add()
    response.name = "ServerReflectionResponse"
    _add_string_field(response, "valid_host", 1)
    original_request = response.field.add()
    original_request.name = "original_request"
    original_request.number = 2
    original_request.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    original_request.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    original_request.type_name = ".grpc.reflection.v1alpha.ServerReflectionRequest"
    response.oneof_decl.add().name = "message_response"
    _add_message_field(response, "file_descriptor_response", 4, ".grpc.reflection.v1alpha.FileDescriptorResponse", oneof_index=0)
    _add_message_field(response, "all_extension_numbers_response", 5, ".grpc.reflection.v1alpha.ExtensionNumberResponse", oneof_index=0)
    _add_message_field(response, "list_services_response", 6, ".grpc.reflection.v1alpha.ListServiceResponse", oneof_index=0)
    _add_message_field(response, "error_response", 7, ".grpc.reflection.v1alpha.ErrorResponse", oneof_index=0)

    file_response = descriptor.message_type.add()
    file_response.name = "FileDescriptorResponse"
    file_descriptor_proto = file_response.field.add()
    file_descriptor_proto.name = "file_descriptor_proto"
    file_descriptor_proto.number = 1
    file_descriptor_proto.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    file_descriptor_proto.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES

    extension_response = descriptor.message_type.add()
    extension_response.name = "ExtensionNumberResponse"
    _add_string_field(extension_response, "base_type_name", 1)
    extension_number = extension_response.field.add()
    extension_number.name = "extension_number"
    extension_number.number = 2
    extension_number.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    extension_number.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32

    list_response = descriptor.message_type.add()
    list_response.name = "ListServiceResponse"
    service = list_response.field.add()
    service.name = "service"
    service.number = 1
    service.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    service.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    service.type_name = ".grpc.reflection.v1alpha.ServiceResponse"

    service_response = descriptor.message_type.add()
    service_response.name = "ServiceResponse"
    _add_string_field(service_response, "name", 1)

    error_response = descriptor.message_type.add()
    error_response.name = "ErrorResponse"
    error_code = error_response.field.add()
    error_code.name = "error_code"
    error_code.number = 1
    error_code.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    error_code.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    _add_string_field(error_response, "error_message", 2)

    service_descriptor = descriptor.service.add()
    service_descriptor.name = "ServerReflection"
    method = service_descriptor.method.add()
    method.name = "ServerReflectionInfo"
    method.input_type = ".grpc.reflection.v1alpha.ServerReflectionRequest"
    method.output_type = ".grpc.reflection.v1alpha.ServerReflectionResponse"
    method.client_streaming = True
    method.server_streaming = True
    return descriptor
####


def _add_string_field(message, name: str, number: int, *, oneof_index: int | None = None) -> None:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    if oneof_index is not None:
        field.oneof_index = oneof_index
    ####
####


def _add_message_field(message, name: str, number: int, type_name: str, *, oneof_index: int | None = None) -> None:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    field.type_name = type_name
    if oneof_index is not None:
        field.oneof_index = oneof_index
    ####
####
