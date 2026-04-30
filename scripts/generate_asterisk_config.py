#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = ROOT / "generated"
GENERATED_AUDIO_DIR = GENERATED_DIR / "audio"
AUDIO_DIR = ROOT / "audio"
INTERNAL_MAILBOX = "1000"
INTERNAL_PIN = "1234"
REGISTERED_PROMPTS = {}
OUTPUT_NAMES = {}


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_config(config_path: Path) -> dict:
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError:
        fail(f"Config file not found: {config_path}")
    except yaml.YAMLError as exc:
        fail(f"Invalid YAML: {exc}")

    if not isinstance(data, dict):
        fail("Top-level YAML structure must be a mapping")
    return data


def require(mapping: dict, key: str, path: str) -> str:
    value = mapping.get(key)
    if value in (None, ""):
        fail(f"Missing required field: {path}.{key}")
    return str(value)


def optional_positive_int(mapping: dict, key: str, path: str, default: int) -> int:
    value = mapping.get(key, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        fail(f"{path}.{key} must be a positive number")
    if parsed < 1:
        fail(f"{path}.{key} must be a positive number")
    return parsed


def safe_audio_stem(filename: str) -> str:
    stem = Path(filename).stem.strip().lower()
    stem = re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-")
    return stem or "prompt"


def prompt_path_for(filename: str) -> Path:
    relative_path = Path(filename)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        fail(f"Prompt must be a file inside the audio directory: {filename}")

    prompt_path = AUDIO_DIR / relative_path
    if not prompt_path.is_file():
        fail(f"Referenced audio file not found: {prompt_path}")
    return prompt_path


def prompt_basename(filename: str) -> str:
    prompt_path = prompt_path_for(filename)
    source_key = str(prompt_path.resolve())

    if source_key not in REGISTERED_PROMPTS:
        safe_stem = safe_audio_stem(filename)
        output_name = f"{safe_stem}.wav"
        existing_source = OUTPUT_NAMES.get(output_name)
        if existing_source and existing_source != source_key:
            fail(
                "Audio filenames must be unique after conversion: "
                f"{filename} conflicts with {Path(existing_source).name}"
            )
        OUTPUT_NAMES[output_name] = source_key
        REGISTERED_PROMPTS[source_key] = {
            "source": prompt_path,
            "output": GENERATED_AUDIO_DIR / output_name,
            "playback": f"custom/{safe_stem}",
        }

    return REGISTERED_PROMPTS[source_key]["playback"]


def probe_audio(prompt_path: Path) -> dict:
    if not shutil.which("ffprobe"):
        fail("Missing required command: ffprobe. Install ffmpeg or run ./deploy.sh.")

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels",
        "-show_entries",
        "format=format_name",
        "-of",
        "json",
        str(prompt_path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        fail(f"Could not read audio format for {prompt_path}: {message}")

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams") or []
    if not streams:
        fail(f"No audio stream found in {prompt_path}")

    return {
        "stream": streams[0],
        "format": data.get("format", {}),
    }


def is_asterisk_wav(prompt_path: Path, metadata: dict) -> bool:
    stream = metadata["stream"]
    format_name = str(metadata["format"].get("format_name", ""))
    return (
        prompt_path.suffix.lower() == ".wav"
        and "wav" in format_name.split(",")
        and stream.get("codec_name") == "pcm_s16le"
        and str(stream.get("sample_rate")) == "8000"
        and int(stream.get("channels") or 0) == 1
    )


def convert_audio_prompts() -> None:
    if not REGISTERED_PROMPTS:
        return

    if not shutil.which("ffmpeg"):
        fail("Missing required command: ffmpeg. Install ffmpeg or run ./deploy.sh.")

    GENERATED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    for prompt in REGISTERED_PROMPTS.values():
        source = prompt["source"]
        output = prompt["output"]
        metadata = probe_audio(source)
        needs_update = not output.exists() or source.stat().st_mtime > output.stat().st_mtime

        if is_asterisk_wav(source, metadata):
            if needs_update:
                shutil.copy2(source, output)
            print(f"Audio OK: {source.name} -> {output.name}")
            continue

        if not needs_update:
            print(f"Audio already converted: {source.name} -> {output.name}")
            continue

        print(f"Converting audio: {source.name} -> {output.name}")
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            "8000",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            fail(f"Could not convert audio file {source}: {exc}")


def validate_options(options: list) -> list:
    if not isinstance(options, list) or not options:
        fail("ivr.options must be a non-empty list")
    if len(options) > 5:
        fail("ivr.options may contain at most 5 entries")

    normalized = []
    seen_digits = set()
    for index, option in enumerate(options, start=1):
        if not isinstance(option, dict):
            fail(f"ivr.options[{index}] must be a mapping")

        digit = require(option, "digit", f"ivr.options[{index}]")
        prompt = require(option, "prompt", f"ivr.options[{index}]")
        action = require(option, "action", f"ivr.options[{index}]").lower()

        if digit in seen_digits:
            fail(f"Duplicate IVR digit: {digit}")
        if len(digit) != 1 or digit not in "0123456789":
            fail(f"ivr.options[{index}].digit must be one digit 0-9")
        seen_digits.add(digit)

        if action not in {"transfer", "voicemail"}:
            fail(f"ivr.options[{index}].action must be transfer or voicemail")

        target = str(option.get("target", "")).strip()
        if action == "transfer" and not target:
            fail(f"ivr.options[{index}].target is required for transfer")
        if action == "voicemail" and target:
            fail(f"ivr.options[{index}].target is not used for voicemail")

        normalized.append(
            {
                "digit": digit,
                "prompt": prompt_basename(prompt),
                "action": action,
                "target": target,
            }
        )

    return normalized


def build_time_condition(windows: list) -> str:
    if not isinstance(windows, list) or not windows:
        fail("ivr.working_hours must be a non-empty list")

    lines = []
    for index, window in enumerate(windows, start=1):
        if not isinstance(window, dict):
            fail(f"ivr.working_hours[{index}] must be a mapping")
        days = require(window, "days", f"ivr.working_hours[{index}]")
        start = require(window, "start", f"ivr.working_hours[{index}]")
        end = require(window, "end", f"ivr.working_hours[{index}]")
        lines.append(f'same => n,GotoIfTime({start}-{end},{days},*,*?ivr-open,s,1)')
    return "\n".join(lines)


def render_pjsip(sip: dict) -> str:
    server = require(sip, "server", "sip")
    username = require(sip, "username", "sip")
    password = require(sip, "password", "sip")

    return f"""[global]
type=global
user_agent=DockerIVR

[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060

[provider-auth]
type=auth
auth_type=userpass
username={username}
password={password}

[provider-aor]
type=aor
contact=sip:{server}

[provider-endpoint]
type=endpoint
transport=transport-udp
context=from-provider
disallow=all
allow=ulaw,alaw
outbound_auth=provider-auth
aors=provider-aor
from_user={username}
from_domain={server}
direct_media=no
rewrite_contact=yes
rtp_symmetric=yes
force_rport=yes

[provider-identify]
type=identify
endpoint=provider-endpoint
match={server}

[provider-registration]
type=registration
transport=transport-udp
outbound_auth=provider-auth
server_uri=sip:{server}
client_uri=sip:{username}@{server}
contact_user={username}
retry_interval=60
forbidden_retry_interval=600
expiration=300
endpoint=provider-endpoint
line=yes
"""


def render_voicemail(client_name: str, mailbox: dict) -> str:
    email = require(mailbox, "email", "ivr.voicemail")
    from_name = require(mailbox, "from_name", "ivr.voicemail")
    from_email = require(mailbox, "from_email", "ivr.voicemail")

    return f"""[general]
format=wav
serveremail={from_email}
fromstring={from_name}
attach=yes
skipms=3000
maxmsg=100
maxsecs=180
mailcmd=/usr/bin/msmtp -t
emailsubject=[{client_name}] New voicemail from ${{VM_CALLERID}}
emailbody=You received a new voicemail from ${{VM_CALLERID}} on ${{VM_DATE}} at ${{VM_DUR}} seconds.

[default]
{INTERNAL_MAILBOX} => {INTERNAL_PIN},{client_name},{email}
"""


def render_msmtp(mailbox: dict) -> str:
    smtp = mailbox.get("smtp")
    if not isinstance(smtp, dict):
        fail("Missing required section: ivr.voicemail.smtp")

    host = require(smtp, "host", "ivr.voicemail.smtp")
    port = require(smtp, "port", "ivr.voicemail.smtp")
    username = require(smtp, "username", "ivr.voicemail.smtp")
    password = require(smtp, "password", "ivr.voicemail.smtp")
    from_email = require(mailbox, "from_email", "ivr.voicemail")
    tls_enabled = str(smtp.get("tls", True)).lower() in {"1", "true", "yes", "on"}
    starttls_enabled = "off" if str(port) == "465" else "on"

    return f"""defaults
auth on
tls {'on' if tls_enabled else 'off'}
tls_starttls {starttls_enabled if tls_enabled else 'off'}
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile /var/log/asterisk/msmtp.log

account default
host {host}
port {port}
from {from_email}
user {username}
password {password}
"""


def render_logger() -> str:
    return """[general]
dateformat=%F %T

[logfiles]
console => notice,warning,error,verbose
messages => notice,warning,error
"""


def render_extensions(config: dict) -> str:
    sip = config["sip"]
    ivr = config["ivr"]
    prompts = ivr["prompts"]
    voicemail = ivr["voicemail"]
    options = validate_options(ivr["options"])

    open_prompt = prompt_basename(require(prompts, "open", "ivr.prompts"))
    closed_prompt = prompt_basename(require(prompts, "closed", "ivr.prompts"))
    invalid_prompt = prompt_basename(require(prompts, "invalid", "ivr.prompts"))
    did = require(sip, "did", "sip")
    time_condition = build_time_condition(ivr["working_hours"])
    timeout_seconds = optional_positive_int(ivr, "timeout_seconds", "ivr", 10)

    option_lines = []
    action_lines = []
    for option in options:
        option_lines.append(f'same => n,GotoIf($["${{IVR_DIGIT}}" = "{option["digit"]}"]?option-{option["digit"]},s,1)')
        action_lines.append(f"[option-{option['digit']}]\nexten => s,1,NoOp(Option {option['digit']})")
        action_lines.append(f" same => n,Playback({option['prompt']})")
        if option["action"] == "transfer":
            action_lines.append(f" same => n,Dial(PJSIP/{option['target']}@provider-endpoint,30)")
        else:
            action_lines.append(f" same => n,VoiceMail({INTERNAL_MAILBOX}@default,u)")
        action_lines.append(" same => n,Hangup()")

    option_branching = "\n".join(option_lines)
    option_contexts = "\n\n".join(action_lines)

    return f"""[general]
static=yes
writeprotect=no
clearglobalvars=no

[globals]
TZ={ivr.get("timezone", "UTC")}

[from-provider]
exten => {did},1,Goto(incoming,s,1)
exten => s,1,Goto(incoming,s,1)
exten => _X.,1,Goto(incoming,s,1)

[incoming]
exten => s,1,NoOp(Incoming IVR call)
 same => n,Set(TIMEZONE=${{TZ}})
{time_condition}
 same => n,Goto(ivr-closed,s,1)

[ivr-open]
exten => s,1,Answer()
 same => n,Playback({open_prompt})
 same => n,Read(IVR_DIGIT,,1,,2,{timeout_seconds})
{option_branching}
 same => n,Playback({invalid_prompt})
 same => n,Goto(ivr-open,s,2)

[ivr-closed]
exten => s,1,Answer()
 same => n,Playback({closed_prompt})
 same => n,VoiceMail({INTERNAL_MAILBOX}@default,u)
 same => n,Hangup()

{option_contexts}
"""


def validate_config(config: dict) -> None:
    if "sip" not in config or not isinstance(config["sip"], dict):
        fail("Missing required section: sip")
    if "ivr" not in config or not isinstance(config["ivr"], dict):
        fail("Missing required section: ivr")
    ivr = config["ivr"]
    if "prompts" not in ivr or not isinstance(ivr["prompts"], dict):
        fail("Missing required section: ivr.prompts")
    if "voicemail" not in ivr or not isinstance(ivr["voicemail"], dict):
        fail("Missing required section: ivr.voicemail")
    prompts = ivr["prompts"]
    prompt_basename(require(prompts, "open", "ivr.prompts"))
    prompt_basename(require(prompts, "closed", "ivr.prompts"))
    prompt_basename(require(prompts, "invalid", "ivr.prompts"))
    validate_options(ivr.get("options", []))
    require(ivr["voicemail"], "email", "ivr.voicemail")
    require(ivr["voicemail"], "from_name", "ivr.voicemail")
    require(ivr["voicemail"], "from_email", "ivr.voicemail")
    smtp = ivr["voicemail"].get("smtp")
    if not isinstance(smtp, dict):
        fail("Missing required section: ivr.voicemail.smtp")
    require(smtp, "host", "ivr.voicemail.smtp")
    require(smtp, "port", "ivr.voicemail.smtp")
    require(smtp, "username", "ivr.voicemail.smtp")
    require(smtp, "password", "ivr.voicemail.smtp")


def write_file(name: str, content: str) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / name
    path.write_text(content, encoding="utf-8")
    print(f"Generated {path}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("Usage: generate_asterisk_config.py <config.yml>")

    config_path = Path(sys.argv[1]).resolve()
    config = load_config(config_path)
    validate_config(config)
    convert_audio_prompts()

    write_file("pjsip.conf", render_pjsip(config["sip"]))
    write_file("extensions.conf", render_extensions(config))
    client_name = str(config.get("client_name", "IVR")).strip() or "IVR"
    write_file("voicemail.conf", render_voicemail(client_name, config["ivr"]["voicemail"]))
    write_file("logger.conf", render_logger())
    write_file("msmtprc", render_msmtp(config["ivr"]["voicemail"]))


if __name__ == "__main__":
    main()
