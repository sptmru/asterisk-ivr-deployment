#!/usr/bin/env bash
set -euo pipefail

mkdir -p /var/spool/asterisk/voicemail /var/log/asterisk /var/run/asterisk

exec /usr/sbin/asterisk -f -U root -G root -vvv
