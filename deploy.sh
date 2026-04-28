#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${ROOT_DIR}/config/client.yml"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Config file not found: ${CONFIG_FILE}" >&2
  echo "Create it from config/client.example.yml first." >&2
  exit 1
fi

require_cmd docker

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "Docker Compose is required." >&2
  exit 1
fi

mkdir -p "${ROOT_DIR}/generated" "${ROOT_DIR}/runtime/voicemail" "${ROOT_DIR}/runtime/log"

"${ROOT_DIR}/scripts/generate_asterisk_config.py" "${CONFIG_FILE}"

cd "${ROOT_DIR}"
"${COMPOSE_CMD[@]}" up -d --build

echo
echo "Asterisk IVR is starting."
echo "Inspect logs with: docker compose logs -f asterisk"
echo "Open CLI with: docker exec -it asterisk-ivr asterisk -rvvv"
