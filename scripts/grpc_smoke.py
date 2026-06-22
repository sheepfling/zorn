from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
####

import grpc  # noqa: E402

from zorn.grpc_api.contract import assert_lattice_grpc_contract  # noqa: E402
from zorn.grpc_api.proto_modules import load_lattice_proto_modules  # noqa: E402


async def run_smoke(args: argparse.Namespace) -> None:
    proto_modules = load_lattice_proto_modules()
    assert_lattice_grpc_contract(proto_modules)
    channel = _build_channel(args)
    async with channel:
        stub = proto_modules.entity_api_grpc.EntityManagerAPIStub(channel)
        entity = proto_modules.entity.Entity(
            entity_id=args.entity_id,
            description=args.description,
            is_live=True,
            no_expiry=True,
        )
        publish_request = proto_modules.entity_api.PublishEntityRequest(entity=entity)
        await stub.PublishEntity(publish_request)
        get_request = proto_modules.entity_api.GetEntityRequest(entity_id=args.entity_id)
        response = await stub.GetEntity(get_request)
        print(response)
    ####
####


def _build_channel(args: argparse.Namespace) -> grpc.aio.Channel:
    if args.tls:
        root_certificates = Path(args.ca_file).read_bytes() if args.ca_file else None
        credentials = grpc.ssl_channel_credentials(root_certificates=root_certificates)
        return grpc.aio.secure_channel(args.target, credentials)
    ####
    return grpc.aio.insecure_channel(args.target)
####


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a minimal EntityManager gRPC compatibility smoke test.")
    parser.add_argument("--target", default="127.0.0.1:50051")
    parser.add_argument("--entity-id", default="zorn-grpc-smoke-entity")
    parser.add_argument("--description", default="gRPC smoke-test entity")
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--ca-file", default=None)
    return parser
####


def main() -> None:
    parser = build_parser()
    asyncio.run(run_smoke(parser.parse_args()))
####


if __name__ == "__main__":
    main()
####
