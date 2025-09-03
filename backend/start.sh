#!/usr/bin/env bash
set -e
python -c "from backend.app.s3_client import ensure_bucket; ensure_bucket()"
python -c "from backend.app.rag.vectorstore import seed_if_empty; seed_if_empty()"
uvicorn backend.app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}
