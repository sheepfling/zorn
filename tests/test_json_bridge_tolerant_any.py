from __future__ import annotations

from typing import cast

from google.protobuf.any_pb2 import Any

from zorn.grpc_api.json_bridge import parse_dict_or_empty


def test_tolerant_parse_preserves_unknown_any_type_url() -> None:
    message = cast(
        Any,
        parse_dict_or_empty(
            Any,
            {"@type": "type.googleapis.com/example.UnknownTask", "foo": "bar"},
        ),
    )

    assert message.type_url == "type.googleapis.com/example.UnknownTask"
    assert b"foo" in message.value
####
