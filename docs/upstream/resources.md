# Upstream research resources

This file is a starting checklist for resources to fetch into `vendor/` or a build cache after license review.

## Public documentation snapshot targets

```bash
mkdir -p docs/upstream/anduril

curl -L https://developer.anduril.com/llms.txt \
  -o docs/upstream/anduril/llms.txt

curl -L https://developer.anduril.com/guides/concepts/overview.md \
  -o docs/upstream/anduril/concepts-overview.md

curl -L https://developer.anduril.com/guides/best-practices/choose-a-protocol.md \
  -o docs/upstream/anduril/choose-a-protocol.md

curl -L https://developer.anduril.com/guides/getting-started/authenticate.md \
  -o docs/upstream/anduril/authenticate.md

curl -L https://developer.anduril.com/reference/rest/entities/publish-entity.md \
  -o docs/upstream/anduril/rest-entities-publish.md

curl -L https://developer.anduril.com/reference/rest/entities/stream-entities.md \
  -o docs/upstream/anduril/rest-entities-stream.md

curl -L https://developer.anduril.com/reference/rest/tasks/create-task.md \
  -o docs/upstream/anduril/rest-tasks-create.md

curl -L https://developer.anduril.com/reference/rest/tasks/stream-as-agent.md \
  -o docs/upstream/anduril/rest-tasks-stream-as-agent.md

curl -L https://developer.anduril.com/reference/rest/tasks/stream-tasks.md \
  -o docs/upstream/anduril/rest-tasks-stream.md

curl -L https://developer.anduril.com/reference/rest/objects/upload-object.md \
  -o docs/upstream/anduril/rest-objects-upload.md

curl -L https://developer.anduril.com/reference/rest/oauth/get-token.md \
  -o docs/upstream/anduril/rest-oauth-token.md
```

## SDK clients for black-box compatibility tests

```bash
python -m pip install anduril-lattice-sdk
npm install @anduril-industries/lattice-sdk

go mod init zorn-research-go
go get github.com/anduril/lattice-sdk-go/v4
```

## Public sample apps to clone as external contract tests

```bash
mkdir -p vendor/anduril-samples
cd vendor/anduril-samples

git clone https://github.com/anduril/sample-app-entity-visualizer
git clone https://github.com/anduril/sample-app-objects
git clone https://github.com/anduril/sample-app-ais-integration-rest
git clone https://github.com/anduril/sample-app-ais-integration-grpc
git clone https://github.com/anduril/sample-app-thumbnail
git clone https://github.com/anduril/sample-app-auto-reconnaissance
```

## Buf/protobuf generation target

```bash
brew install bufbuild/buf/buf
buf build buf.build/anduril/lattice-sdk

go get buf.build/gen/go/anduril/lattice-sdk/grpc/go@latest
go get buf.build/gen/go/anduril/lattice-sdk/protocolbuffers/go@latest
```

## Safety note

Avoid unofficial packages with similar names unless they have been independently vetted. Treat public SDKs and generated code as external clients/contracts until their licenses are reviewed for the intended use.


## gRPC / protobuf source of truth

- Buf module: `buf.build/anduril/lattice-sdk`
- Python generated package index: `https://buf.build/gen/python`
- Python generated packages used by current public gRPC sample apps:
  - `anduril-lattice-sdk-grpc-python==1.80.0.1.20260515215502`
  - `anduril-lattice-sdk-protocolbuffers-python==34.1.0.1.20260515215502`
  - `anduril-lattice-sdk-protocolbuffers-pyi==34.1.0.1.20260515215502`
- Local implementation rule: no hand-maintained `.proto` copies in Zorn; use the official generated artifacts as runtime dependencies.
