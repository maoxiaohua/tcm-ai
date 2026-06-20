#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

load_runtime_env() {
  local env_file="$1"
  [[ -f "${env_file}" ]] || return 0

  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" || "${line:0:1}" == "#" ]] && continue

    key="${line%%=*}"
    value="${line#*=}"
    value="${value%$'\r'}"

    case "${key}" in
      HOST|PORT|WORKERS)
        target_key="${key}"
        ;;
      SERVER_HOST)
        target_key="HOST"
        ;;
      SERVER_PORT)
        target_key="PORT"
        ;;
      UVICORN_WORKERS)
        target_key="WORKERS"
        ;;
      *)
        continue
        ;;
    esac

    if [[ -z "${!target_key:-}" ]]; then
      export "${target_key}=${value}"
    fi
  done < "${env_file}"
}

load_runtime_env "${PROJECT_ROOT}/config/.env"
load_runtime_env "${PROJECT_ROOT}/.env"

exec uvicorn app.factory:create_app \
  --factory \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}" \
  --reload \
  --reload-dir app \
  --reload-dir api \
  --reload-dir core \
  --reload-dir services \
  --reload-dir database \
  --reload-dir config
