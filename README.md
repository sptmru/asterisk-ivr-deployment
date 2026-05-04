# Dockerized Asterisk IVR

This repository provides a simple, client-configurable IVR deployment for Ubuntu 24.04.

For a step-by-step guide written for a non-technical operator, including SSH, cloning this repository, uploading audio files, editing the config, and running the deployment, see [NON_TECHNICAL_GUIDE.md](NON_TECHNICAL_GUIDE.md).

For a Windows client workflow that uses `key.txt` beside a PowerShell script to connect to the server and run the deployment, see [WINDOWS_CLIENT_GUIDE.md](WINDOWS_CLIENT_GUIDE.md).

The workflow is:

1. Put the client YAML file in `config/client.yml`.
2. Put referenced audio files in `audio/`.
3. Run `./deploy.sh`.

The deploy script:

1. Installs Docker, Docker Compose, `python3-yaml`, and `ffmpeg` on Ubuntu 24.04 if they are missing.
2. Detects referenced audio formats and converts prompts when needed.
3. Generates Asterisk configuration from the YAML file.
4. Builds the Docker image.
5. Starts Asterisk with the generated IVR.

## Layout

- `config/client.example.yml`: sample client configuration
- `audio/`: source prompts referenced by the YAML
- `generated/audio/`: Asterisk-ready prompts generated from `audio/`
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

Add the audio files referenced by the config into `audio/`.

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
- A configurable timeout for how long callers have to press an IVR option, followed by a timeout prompt and voicemail
- Up to five IVR options
- Each option can transfer to a phone number, send the caller to voicemail, or play a prompt before timing out to voicemail
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

IVR digit timeout format:

```yaml
timeout_seconds: 10
prompts:
  timeout: timeout.wav
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

- Prompts can be common audio files such as WAV, MP3, M4A, FLAC, or OGG. `./deploy.sh` converts them into Asterisk-ready 8 kHz mono PCM WAV files under `generated/audio/`.
- Prompt filenames must be unique after removing the extension. For example, do not reference both `welcome.mp3` and `welcome.wav`.
- This project uses `chan_pjsip`.
- SIP signaling uses UDP 5060 and RTP uses UDP 10000-10100 on the host.
- The container is granted `NET_ADMIN` because Ubuntu's Asterisk package installs that Linux capability during startup.
- Inbound routing sends calls to the configured DID when available, with a fallback to `s`.
- The mailbox number is internal now. The client only fills in the voicemail email and SMTP settings.
- Use an SMTP account that allows app passwords or relay auth.
- Voicemail email delivery uses `msmtp`; SMTP delivery failures are written inside the container to `/var/log/asterisk/msmtp.log`, which is mounted at `runtime/log/msmtp.log` on the host.
