#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${ROOT_DIR}/config/client.yml"
APT_UPDATED=0

run_as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

ensure_apt_updated() {
  if [[ "${APT_UPDATED}" -eq 0 ]]; then
    run_as_root apt-get update
    APT_UPDATED=1
  fi
}

install_package_if_missing() {
  local cmd="$1"
  local package="$2"

  if command -v "${cmd}" >/dev/null 2>&1; then
    return
  fi

  echo "Installing missing dependency: ${package}"
  ensure_apt_updated
  export DEBIAN_FRONTEND=noninteractive
  run_as_root apt-get install -y "${package}"
}

ensure_python_yaml() {
  if python3 -c "import yaml" >/dev/null 2>&1; then
    return
  fi

  echo "Installing missing dependency: python3-yaml"
  ensure_apt_updated
  export DEBIAN_FRONTEND=noninteractive
  run_as_root apt-get install -y python3-yaml
}

ensure_docker_running() {
  if systemctl is-active --quiet docker; then
    return
  fi

  run_as_root systemctl enable --now docker
}

ensure_docker_group() {
  if ! getent group docker >/dev/null 2>&1; then
    run_as_root groupadd docker
  fi

  if [[ "$(id -u)" -ne 0 ]]; then
    run_as_root usermod -aG docker "${USER}" || true
  fi
}

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

install_package_if_missing python3 python3
ensure_python_yaml
install_package_if_missing docker docker.io
ensure_docker_running
ensure_docker_group

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "Installing missing dependency: docker-compose-v2"
  ensure_apt_updated
  export DEBIAN_FRONTEND=noninteractive
  run_as_root apt-get install -y docker-compose-v2
  COMPOSE_CMD=(docker compose)
fi

mkdir -p \
  "${ROOT_DIR}/generated" \
  "${ROOT_DIR}/runtime/lib/sounds" \
  "${ROOT_DIR}/runtime/voicemail" \
  "${ROOT_DIR}/runtime/log"

"${ROOT_DIR}/scripts/generate_asterisk_config.py" "${CONFIG_FILE}"

cd "${ROOT_DIR}"
"${COMPOSE_CMD[@]}" up -d --build

echo
echo "Asterisk IVR is starting."
echo "Inspect logs with: docker compose logs -f asterisk"
echo "Open CLI with: docker exec -it asterisk-ivr asterisk -rvvv"
echo "If docker access is still denied, log out and back in once, then rerun ./deploy.sh."
