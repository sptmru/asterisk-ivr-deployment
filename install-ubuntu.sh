#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "deploy.sh already installs everything it needs."
echo "Continuing with the full deployment flow..."
echo

exec "${SCRIPT_DIR}/deploy.sh"
