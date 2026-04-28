#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = ROOT / "generated"
AUDIO_DIR = ROOT / "audio"
INTERNAL_MAILBOX = "1000"
INTERNAL_PIN = "1234"


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


def prompt_basename(filename: str) -> str:
    if not filename.lower().endswith(".wav"):
        fail(f"Prompt must be a .wav file: {filename}")

    prompt_path = AUDIO_DIR / filename
    if not prompt_path.is_file():
        fail(f"Referenced audio file not found: {prompt_path}")

    return f"custom/{prompt_path.stem}"


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
 same => n,Read(IVR_DIGIT,,1,,2,5)
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

    write_file("pjsip.conf", render_pjsip(config["sip"]))
    write_file("extensions.conf", render_extensions(config))
    client_name = str(config.get("client_name", "IVR")).strip() or "IVR"
    write_file("voicemail.conf", render_voicemail(client_name, config["ivr"]["voicemail"]))
    write_file("logger.conf", render_logger())
    write_file("msmtprc", render_msmtp(config["ivr"]["voicemail"]))


if __name__ == "__main__":
    main()
