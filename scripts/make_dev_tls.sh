#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-var/certs}"
PRODUCT_NAME="${C2_COMPAT_PRODUCT_NAME:-C2 Compat Sandbox}"
mkdir -p "${OUT_DIR}"

cat > "${OUT_DIR}/server.ext" <<'EOF'
subjectAltName = DNS:localhost,IP:127.0.0.1
extendedKeyUsage = serverAuth
EOF

openssl genrsa -out "${OUT_DIR}/dev-ca-key.pem" 4096
openssl req -x509 -new -nodes \
  -key "${OUT_DIR}/dev-ca-key.pem" \
  -sha256 \
  -days 3650 \
  -subj "/CN=${PRODUCT_NAME} Dev CA" \
  -out "${OUT_DIR}/dev-ca.pem"

openssl genrsa -out "${OUT_DIR}/server-key.pem" 2048
openssl req -new \
  -key "${OUT_DIR}/server-key.pem" \
  -subj "/CN=localhost" \
  -out "${OUT_DIR}/server.csr"

openssl x509 -req \
  -in "${OUT_DIR}/server.csr" \
  -CA "${OUT_DIR}/dev-ca.pem" \
  -CAkey "${OUT_DIR}/dev-ca-key.pem" \
  -CAcreateserial \
  -out "${OUT_DIR}/server.pem" \
  -days 365 \
  -sha256 \
  -extfile "${OUT_DIR}/server.ext"

echo "Wrote development TLS files to ${OUT_DIR}"
