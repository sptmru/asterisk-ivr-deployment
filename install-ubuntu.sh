#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

export DEBIAN_FRONTEND=noninteractive

${SUDO} apt-get update
${SUDO} apt-get install -y \
  ca-certificates \
  curl \
  docker.io \
  docker-compose-v2 \
  python3 \
  python3-yaml

${SUDO} systemctl enable --now docker

if ! getent group docker >/dev/null 2>&1; then
  ${SUDO} groupadd docker
fi

if [[ -n "${SUDO}" ]]; then
  ${SUDO} usermod -aG docker "${SUDO_USER:-$USER}" || true
fi

echo
echo "Installation complete."
echo "You may need to log out and back in before running docker without sudo."
