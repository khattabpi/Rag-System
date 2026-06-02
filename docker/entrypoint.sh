#!/bin/bash
set -e

echo "[*] Verifying service connectivity interfaces..."

# Loop block verifying Qdrant's HTTP readiness
until curl -s "http://${QDRANT_HOST:-qdrant-db}:${QDRANT_PORT:-6333}/readyz" | grep -q "ready"; do
  echo "[-] Qdrant Engine unavailable. Retrying in 3 seconds..."
  sleep 3
done
echo "[+] Connected to Qdrant storage array server."

# Start application server core bound across standard port configurations
exec uvicorn api.main:app --host 0.0.0.0 --port 8000