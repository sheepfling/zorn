# Go gRPC smoke target

After generating the official Buf artifacts and starting the local gRPC server,
you can use a Go client with the same import style shown in Anduril's public
docs:

```go
import (
    "buf.build/gen/go/anduril/lattice-sdk/grpc/go/anduril/entitymanager/v1/entitymanagerv1grpc"
    entitymanagerv1 "buf.build/gen/go/anduril/lattice-sdk/protocolbuffers/go/anduril/entitymanager/v1"
)
```

This folder is intentionally only a note for now. The Python smoke script under
`scripts/grpc_smoke.py` is the first executable gRPC contract check because it can
share the locally generated Python stubs used by the server.
