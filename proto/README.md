# Proto source of truth

Zorn does not maintain hand-written copies of Lattice protobuf files.
The compatibility target is the official public Buf module:

```text
buf.build/anduril/lattice-sdk
```

For normal development, install the Buf-generated Python packages instead of
checking generated files into this repo:

```bash
./scripts/install_grpc_deps.sh
```

To inspect or archive the upstream `.proto` files and descriptor set locally:

```bash
brew install bufbuild/buf/buf
./scripts/export_lattice_protos.sh
```

Generated or exported files should be treated as vendor artifacts. Do not edit
them and do not replace them with local lookalike proto definitions.


## Audit commands

```bash
make proto-contract-report
make proto-export
```

`make proto-contract-report` validates the installed Buf-generated service descriptors. `make proto-export` exports the public upstream `.proto` files for inspection under `vendor/lattice-sdk-protos`.
