#!/usr/bin/env bash
set -euo pipefail

mkdir -p \
  /var/lib/asterisk \
  /var/lib/asterisk/agi-bin \
  /usr/share/asterisk/sounds/custom \
  /var/spool/asterisk/voicemail \
  /var/spool/asterisk/voicemail/default \
  /var/spool/asterisk/voicemail/default/1000 \
  /var/spool/asterisk/voicemail/default/1000/tmp \
  /var/spool/asterisk/voicemail/default/1000/INBOX \
  /var/spool/asterisk/voicemail/default/1000/Old \
  /var/spool/asterisk/voicemail/default/1000/Urgent \
  /var/log/asterisk \
  /var/run/asterisk

chown -R asterisk:asterisk \
  /var/lib/asterisk \
  /var/spool/asterisk/voicemail \
  /var/log/asterisk \
  /var/run/asterisk
chmod -R u+rwX,g+rwX,o+rwX \
  /var/lib/asterisk \
  /var/spool/asterisk/voicemail \
  /var/log/asterisk \
  /var/run/asterisk

echo "Asterisk startup spool check:"
id
stat -c "%U:%G %a %n" \
  /var/spool \
  /var/spool/asterisk \
  /var/spool/asterisk/voicemail \
  /var/spool/asterisk/voicemail/default \
  /var/spool/asterisk/voicemail/default/1000 \
  /var/spool/asterisk/voicemail/default/1000/tmp

exec /usr/sbin/asterisk -f -U asterisk -G asterisk -vvv
