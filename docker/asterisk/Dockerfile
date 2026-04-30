FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asterisk \
        asterisk-core-sounds-en-wav \
        asterisk-moh-opsound-wav \
        asterisk-voicemail \
        ca-certificates \
        msmtp-mta \
    && rm -rf /var/lib/apt/lists/*

COPY docker/asterisk/modules.conf /etc/asterisk/modules.conf
COPY docker/asterisk/asterisk.conf /etc/asterisk/asterisk.conf
COPY docker/asterisk/rtp.conf /etc/asterisk/rtp.conf
COPY docker/asterisk/start.sh /start.sh

RUN chmod +x /start.sh \
    && mkdir -p \
        /var/lib/asterisk \
        /var/lib/asterisk/agi-bin \
        /usr/share/asterisk/sounds/custom \
        /var/spool/asterisk/voicemail \
        /var/log/asterisk \
        /var/run/asterisk

CMD ["/start.sh"]
