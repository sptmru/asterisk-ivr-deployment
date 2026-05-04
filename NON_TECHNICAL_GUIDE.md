# IVR Deployment Guide

This guide explains how to put this IVR system on a new server, upload the greeting audio files, edit the client settings, and start the phone system.

The server must run **Ubuntu 24.04 LTS**.

## What This System Does

This project runs an Asterisk IVR in Docker. In plain language:

- Callers dial your phone number.
- During working hours, they hear the open-hours greeting and can press menu options.
- Outside working hours, they hear the closed-hours greeting and go directly to voicemail.
- Voicemails are sent to the email address configured in `config/client.yml`.

You normally edit only two places:

- `config/client.yml`: phone provider, working hours, menu options, and voicemail email settings
- `audio/`: the WAV or other audio files used as greetings and menu prompts

Do not manually edit files in `generated/`. They are recreated automatically.

## What You Need Before Starting

Ask your server provider, phone provider, or technical contact for these details:

- A server running **Ubuntu 24.04 LTS**
- The server IP address, for example `203.0.113.10`
- SSH login details, usually one of these:
  - username and password
  - username and SSH key file
- SIP phone provider details:
  - SIP server
  - SIP username
  - SIP password
  - phone number / DID
- Voicemail email delivery details:
  - email address that should receive voicemails
  - SMTP server
  - SMTP port, usually `587`
  - SMTP username
  - SMTP password or app password
- Audio prompt files, for example:
  - `welcome-open.wav`
  - `welcome-closed.wav`
  - `invalid-option.wav`
  - `timeout.wav`
  - `sales.wav`
  - `support.wav`
  - `voicemail.wav`
  - `callback-message.wav`

The audio files may be WAV, MP3, M4A, FLAC, or OGG. The deploy script converts them automatically.

## Server Requirements

Use a clean server with **Ubuntu 24.04 LTS** as the operating system.

## Step 1: Open a Terminal on Your Computer

On macOS:

1. Open **Terminal**.

On Windows:

1. Open **PowerShell** or **Windows Terminal**.

All commands in the next steps are typed in that terminal.

## Step 2: Connect to the Server by SSH

Use the username and server IP address from your hosting provider.

Example:

```bash
ssh ubuntu@203.0.113.10
```

Replace:

- `ubuntu` with your real server username
- `203.0.113.10` with your real server IP address

If your provider gave you an SSH key file, the command may look like this:

```bash
ssh -i ~/Downloads/server-key.pem ubuntu@203.0.113.10
```

The first time you connect, SSH may ask:

```text
Are you sure you want to continue connecting?
```

Type:

```text
yes
```

Then press Enter.

After you log in successfully, your terminal is now controlling the server.

## Step 3: Clone This Repository

Run this command on the server:

```bash
git clone https://github.com/sptmru/asterisk-ivr-deployment.git
```

Go into the project folder:

```bash
cd asterisk-ivr-deployment
```

From now on, run commands from inside this folder unless the guide says otherwise.

## Step 4: Create the Client Config File

The project includes an example config. Copy it to the real config file:

```bash
cp config/client.example.yml config/client.yml
```

Open it for editing:

```bash
nano config/client.yml
```

You will see a file similar to this:

```yaml
client_name: sample-client

sip:
  server: sip.example.com
  username: "100100"
  password: change-me
  did: "15551234567"

ivr:
  timezone: UTC
  timeout_seconds: 30
  working_hours:
    - days: mon-fri
      start: "09:00"
      end: "18:00"
    - days: sat
      start: "10:00"
      end: "14:00"
  prompts:
    open: welcome-open.wav
    closed: welcome-closed.wav
    invalid: invalid-option.wav
    timeout: timeout.wav
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
  options:
    - digit: "1"
      prompt: sales.wav
      action: transfer
      target: "15550101"
    - digit: "2"
      prompt: support.wav
      action: transfer
      target: "15550102"
    - digit: "3"
      prompt: voicemail.wav
      action: voicemail
    - digit: "4"
      prompt: callback-message.wav
      action: play
```

### What to Change

Change `client_name` to a short name for the client or company.

Change the `sip` section using details from the SIP phone provider:

```yaml
sip:
  server: your-sip-server.example.com
  username: "your-sip-username"
  password: your-sip-password
  did: "your-phone-number"
```

Change the timezone. For example:

```yaml
timezone: America/New_York
```

Other examples:

- `America/Los_Angeles`
- `America/Chicago`
- `Europe/London`
- `Asia/Yerevan`

Change working hours:

```yaml
working_hours:
  - days: mon-fri
    start: "09:00"
    end: "18:00"
```

The time format is 24-hour time:

- `09:00` means 9:00 AM
- `18:00` means 6:00 PM

Change the audio prompt filenames:

```yaml
prompts:
  open: welcome-open.wav
  closed: welcome-closed.wav
  invalid: invalid-option.wav
  timeout: timeout.wav
```

These filenames must match the files you will upload into the `audio/` folder.

Change voicemail email settings:

```yaml
voicemail:
  email: manager@example.com
  from_name: Company IVR
  from_email: ivr@example.com
  smtp:
    host: smtp.example.com
    port: 587
    username: ivr@example.com
    password: app-password
    tls: true
```

Change menu options:

```yaml
options:
  - digit: "1"
    prompt: sales.wav
    action: transfer
    target: "15550101"
  - digit: "2"
    prompt: support.wav
    action: transfer
    target: "15550102"
  - digit: "3"
    prompt: voicemail.wav
    action: voicemail
  - digit: "4"
    prompt: callback-message.wav
    action: play
```

For a transfer option:

- `digit` is what the caller presses
- `prompt` is the audio file that explains the option
- `action` should be `transfer`
- `target` is the phone number to transfer to

For a voicemail option:

- `digit` is what the caller presses
- `prompt` is the audio file that explains the option
- `action` should be `voicemail`
- there is no `target`

For a play option:

- `digit` is what the caller presses
- `prompt` is the audio file to play before waiting
- `action` should be `play`
- there is no `target`
- after the prompt, the system plays hold music for `timeout_seconds`, plays the timeout prompt, and records voicemail

### How to Save in Nano

When finished editing:

1. Press `Ctrl + O`
2. Press Enter
3. Press `Ctrl + X`

## Step 5: Upload the Audio Files

The audio files must be placed in the project `audio/` folder on the server.

You can upload them with `scp` from your own computer, or with an SFTP app such as FileZilla, Cyberduck, or WinSCP.

### Option A: Upload with scp

Open a second terminal on your own computer. This terminal should not be connected to the server.

If your audio files are in your local `Downloads` folder, run:

```bash
scp ~/Downloads/*.wav ubuntu@203.0.113.10:~/asterisk-ivr-deployment/audio/
```

Replace:

- `ubuntu` with your server username
- `203.0.113.10` with your server IP address
- `~/Downloads/*.wav` with the real location of your audio files

If you use an SSH key file, the command may look like this:

```bash
scp -i ~/Downloads/server-key.pem ~/Downloads/*.wav ubuntu@203.0.113.10:~/asterisk-ivr-deployment/audio/
```

You can also upload MP3, M4A, FLAC, or OGG files. Use the command that matches your file type:

```bash
scp ~/Downloads/*.mp3 ubuntu@203.0.113.10:~/asterisk-ivr-deployment/audio/
scp ~/Downloads/*.m4a ubuntu@203.0.113.10:~/asterisk-ivr-deployment/audio/
scp ~/Downloads/*.flac ubuntu@203.0.113.10:~/asterisk-ivr-deployment/audio/
scp ~/Downloads/*.ogg ubuntu@203.0.113.10:~/asterisk-ivr-deployment/audio/
```

If a command says some files were not found, that is okay when you do not have that file type.

### Option B: Upload with an SFTP App

Use these connection details:

- Protocol: SFTP
- Host: your server IP address
- Username: your server username
- Password or SSH key: from your hosting provider

After connecting, open this folder on the server:

```text
/home/ubuntu/asterisk-ivr-deployment/audio/
```

If your username is not `ubuntu`, replace `ubuntu` in the path with your username.

Upload all prompt files into that folder.

### Check Uploaded Files

Back in the SSH terminal on the server, run:

```bash
ls -lah audio
```

You should see your uploaded audio files.

Important: every filename used in `config/client.yml` must exist in `audio/`.

## Step 6: Start the IVR

In the SSH terminal on the server, make sure you are inside the project folder:

```bash
cd ~/asterisk-ivr-deployment
```

Run:

```bash
./deploy.sh
```

The first run may take several minutes. It may install Docker, Docker Compose, Python YAML support, and ffmpeg.

If it asks for your password, type your server password and press Enter.

When it finishes, you should see:

```text
Asterisk IVR is starting.
```

The IVR should now be running.

## Step 7: Check That It Is Running

Run:

```bash
docker compose ps
```

You should see a service named `asterisk` or a container named `asterisk-ivr`.

To watch the logs:

```bash
docker compose logs -f asterisk
```

Press `Ctrl + C` to stop watching logs. This does not stop the IVR.

## Step 8: Test the Phone Number

Call the phone number configured in the SIP provider.

During working hours:

- You should hear the open-hours greeting.
- You should be able to press menu options.
- Transfer options should call the configured target phone numbers.
- Voicemail options should record a voicemail and email it.

Outside working hours:

- You should hear the closed-hours greeting.
- The call should go directly to voicemail.
- Other IVR menu options should not run.

## Making Changes Later

To change phone numbers, working hours, voicemail email settings, or menu options:

```bash
cd ~/asterisk-ivr-deployment
nano config/client.yml
./deploy.sh
```

To replace audio files:

1. Upload the new files into `audio/`.
2. Make sure the filenames match `config/client.yml`.
3. Run:

```bash
cd ~/asterisk-ivr-deployment
./deploy.sh
```

The deploy script regenerates the Asterisk files and restarts the container.

## Stopping and Restarting

To stop the IVR:

```bash
cd ~/asterisk-ivr-deployment
docker compose down
```

To start it again:

```bash
cd ~/asterisk-ivr-deployment
./deploy.sh
```

To restart after a server reboot:

```bash
cd ~/asterisk-ivr-deployment
./deploy.sh
```

## Updating the Project from GitHub

If a technical contact tells you that the GitHub project was updated, run:

```bash
cd ~/asterisk-ivr-deployment
git pull
./deploy.sh
```

This downloads the latest project files and restarts the IVR with your existing config and audio files.

## Common Problems

### The server says `Config file not found`

Create the config file:

```bash
cp config/client.example.yml config/client.yml
```

Then edit it:

```bash
nano config/client.yml
```

### The deploy script says an audio file is missing

Check the filenames in `config/client.yml`.

Then check the uploaded files:

```bash
ls -lah audio
```

The names must match exactly, including uppercase/lowercase letters.

For example, `Welcome.wav` and `welcome.wav` are different names on Linux.

### Docker permission is denied

Run the deploy script again:

```bash
./deploy.sh
```

If it still says Docker permission is denied, log out of SSH:

```bash
exit
```

Then connect again:

```bash
ssh ubuntu@203.0.113.10
```

Go back to the project folder and rerun deploy:

```bash
cd ~/asterisk-ivr-deployment
./deploy.sh
```

### Calls connect but there is no audio

Ask the server provider or firewall administrator to confirm these UDP ports are open:

- `5060`
- `10000-10100`

Also confirm the SIP provider allows traffic from the server IP address.

### Voicemail emails are not arriving

Check the SMTP settings in `config/client.yml`.

Then check the email log:

```bash
cat runtime/log/msmtp.log
```

Common causes:

- wrong SMTP username
- wrong SMTP password
- normal email password used instead of an app password
- SMTP provider blocks server logins
- wrong SMTP host or port

### The IVR does not answer calls

Check the logs:

```bash
docker compose logs -f asterisk
```

Also confirm:

- SIP server, username, password, and DID are correct
- the SIP provider has the server IP address allowed
- UDP port `5060` is open

## Useful Commands

Run these commands from the project folder on the server:

```bash
cd ~/asterisk-ivr-deployment
```

Check running containers:

```bash
docker compose ps
```

Watch logs:

```bash
docker compose logs -f asterisk
```

Stop the IVR:

```bash
docker compose down
```

Start or redeploy the IVR:

```bash
./deploy.sh
```

List audio files:

```bash
ls -lah audio
```

Edit config:

```bash
nano config/client.yml
```
