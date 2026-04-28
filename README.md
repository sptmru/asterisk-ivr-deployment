# Dockerized Asterisk IVR

This repository provides a simple, client-configurable IVR deployment for Ubuntu 24.04.

The workflow is:

1. Run `./install-ubuntu.sh` once on a clean Ubuntu 24.04 server.
2. Put the client YAML file in `config/client.yml`.
3. Put referenced WAV files in `audio/`.
4. Run `./deploy.sh`.

The deploy script:

1. Verifies Docker and Docker Compose are available.
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

## Quick start

Copy the example config:

```bash
cp config/client.example.yml config/client.yml
```

On a clean Ubuntu 24.04 host, install prerequisites first:

```bash
./install-ubuntu.sh
```

Add the WAV files referenced by the config into `audio/`.

Generate and start the stack:

```bash
./deploy.sh
```

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

## Notes

- Prompts must be `.wav` files that Asterisk can play. Standard PCM WAV works best.
- This project uses `chan_pjsip`.
- SIP signaling uses UDP 5060 and RTP uses UDP 10000-10100 on the host.
- Inbound routing sends calls to the configured DID when available, with a fallback to `s`.
- Voicemail here means "leave a message" rather than mailbox retrieval.
- The deploy generator uses `python3-yaml`, installed by `install-ubuntu.sh`.
