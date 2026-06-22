.PHONY: test run grpc-run grpc-smoke grpcurl-checks compat-matrix sample-app-objects sample-app-ais-rest contract-smoke proto-contract-report proto-export fetch-upstream-docs grpc-deps

test:
	pytest

run:
	uvicorn zorn.main:app --reload --port 8080

grpc-run:
	zorn-grpc

grpc-smoke:
	python scripts/grpc_smoke.py --target 127.0.0.1:50051

grpcurl-checks:
	scripts/run_grpcurl_checks.sh 127.0.0.1:50051

compat-matrix:
	python scripts/compat_matrix.py

sample-app-objects:
	scripts/run_sample_app_objects.sh

sample-app-ais-rest:
	scripts/run_sample_app_ais_rest.sh

grpc-deps:
	scripts/generate_lattice_grpc_python.sh

proto-contract-report:
	python scripts/proto_contract_report.py --assert --pretty

proto-export:
	scripts/export_lattice_protos.sh

contract-smoke:
	python scripts/contract_smoke.py

fetch-upstream-docs:
	scripts/fetch_upstream_docs.sh
