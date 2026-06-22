# Sample app contract plan

The local server should be validated by black-box sample-app runners. The runners should not copy third-party sample code into this repository. Instead, they should clone or point at sample repositories in a local `vendor/` directory and run them against `http://127.0.0.1:8080` with a dev token.

## Compatibility goal

A sample app should run with only endpoint/token configuration changes. Any code patch required in a sample app should create a compatibility issue in this repo.

## Initial sample-app order

1. Object upload/list/get sample.
2. AIS REST integration sample.
3. Entity visualizer sample.
4. Thumbnail sample.
5. Auto reconnaissance/tasking sample.
6. AIS gRPC integration sample after the gRPC facade exists.

## Runner pattern

Each runner should:

1. Start the local API with an isolated SQLite database and object root.
2. Seed any needed entities/tasks/objects.
3. Run the sample app as an external process.
4. Assert against local API state, event logs, or object metadata.
5. Save stdout/stderr under `var/contract-runs/` for debugging.

## Local environment contract

Use neutral names so the codename can change later:

```bash
C2_COMPAT_PRODUCT_NAME=Zorn
C2_COMPAT_AUTH_MODE=none
C2_COMPAT_DATABASE_URL=sqlite:///./var/contract.db
C2_COMPAT_OBJECT_ROOT=./var/contract-objects
```

Suggested public-SDK-facing aliases for external sample apps:

```bash
LATTICE_BASE_URL=http://127.0.0.1:8080
LATTICE_TOKEN=dev-token
```

The runner can translate sample-specific environment variables without hardcoding them in the server.
