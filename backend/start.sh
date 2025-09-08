#!/usr/bin/env bash
set -e

for i in {1..30}; do
  python -c "from backend.app.s3_client import ensure_bucket; ensure_bucket()" && break || true
  echo "[backend] MinIO not ready yet, retrying..."
  sleep 2
done

exec uvicorn backend.app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
