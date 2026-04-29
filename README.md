# Dockerized Asterisk IVR

This repository provides a simple, client-configurable IVR deployment for Ubuntu 24.04.

The workflow is:

1. Put the client YAML file in `config/client.yml`.
2. Put referenced WAV files in `audio/`.
3. Run `./deploy.sh`.

The deploy script:

1. Installs Docker, Docker Compose, and `python3-yaml` on Ubuntu 24.04 if they are missing.
2. Generates Asterisk configuration from the YAML file.
3. Builds the Docker image.
4. Starts Asterisk with the generated IVR.

## Layout

- `config/client.example.yml`: sample client configuration
- `audio/`: WAV prompts referenced by the YAML
- `scripts/generate_asterisk_config.py`: renders Asterisk config files
- `docker/asterisk/`: container image assets
- `generated/`: generated Asterisk config files
- `deploy.sh`: one-command deployment entry point
- `install-ubuntu.sh`: compatibility wrapper that just calls `deploy.sh`

## Quick start

Copy the example config:

```bash
cp config/client.example.yml config/client.yml
```

Add the WAV files referenced by the config into `audio/`.

Generate and start the stack:

```bash
./deploy.sh
```

The script will ask for `sudo` if Docker or `python3-yaml` still need to be installed.

To stop it later:

```bash
docker compose down
```

## YAML format

The config supports:

- SIP registration data: provider server, username, password, DID
- Two greetings: working-hours and closed-hours
- One or more working-hour windows
- Up to five IVR options
- Each option can transfer to a phone number or send the caller to voicemail
- Voicemail delivery by email through an SMTP account

Supported schedule format:

```yaml
working_hours:
  - days: mon-fri
    start: "09:00"
    end: "18:00"
  - days: sat
    start: "10:00"
    end: "14:00"
```

Voicemail email format:

```yaml
voicemail:
  email: hello@example.com
  from_name: Sample Client IVR
  from_email: ivr@example.com
  smtp:
    host: smtp.example.com
    port: 587
    username: ivr@example.com
    password: app-password
    tls: true
```

## Notes

- Prompts must be `.wav` files that Asterisk can play. Standard PCM WAV works best.
- This project uses `chan_pjsip`.
- SIP signaling uses UDP 5060 and RTP uses UDP 10000-10100 on the host.
- The container is granted `NET_ADMIN` because Ubuntu's Asterisk package installs that Linux capability during startup.
- Inbound routing sends calls to the configured DID when available, with a fallback to `s`.
- The mailbox number is internal now. The client only fills in the voicemail email and SMTP settings.
- Use an SMTP account that allows app passwords or relay auth.
