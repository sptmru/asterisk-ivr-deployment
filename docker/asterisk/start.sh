#!/usr/bin/env bash
set -euo pipefail

mkdir -p \
  /var/lib/asterisk \
  /var/lib/asterisk/agi-bin \
  /usr/share/asterisk/sounds/custom \
  /var/spool/asterisk/voicemail \
  /var/spool/asterisk/voicemail/default/1000/tmp \
  /var/log/asterisk \
  /var/run/asterisk

chmod -R u+rwX,g+rwX,o+rwX \
  /var/lib/asterisk \
  /var/spool/asterisk/voicemail \
  /var/log/asterisk \
  /var/run/asterisk

exec /usr/sbin/asterisk -f -U root -G root -vvv
