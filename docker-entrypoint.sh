#!/bin/sh
set -eu

DATA_DIR="${DATA_DIR:-/app/data}"
SEED_DIR="${SEED_DIR:-/app/seed_data}"

mkdir -p \
  "$DATA_DIR" \
  "$DATA_DIR/hr_request_attachments" \
  "$DATA_DIR/landing/uploads" \
  "$DATA_DIR/standardized/news" \
  "$DATA_DIR/index"

if [ -d "$SEED_DIR" ]; then
  cp -an "$SEED_DIR"/. "$DATA_DIR"/ 2>/dev/null || true
fi

exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
