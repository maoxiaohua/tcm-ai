#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

exec uvicorn app.factory:create_app \
  --factory \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --reload \
  --reload-dir app \
  --reload-dir api \
  --reload-dir core \
  --reload-dir services \
  --reload-dir database \
  --reload-dir config

