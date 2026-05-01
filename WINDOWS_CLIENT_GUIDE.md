# Windows One-Click Deployment Guide

This guide is for a client using Windows. It uses `deploy-windows.ps1` to connect to the Ubuntu server, clone or update the IVR project, upload the config and audio files, and run the deployment.

The server must run **Ubuntu 24.04 LTS**.

## Folder Layout on Your Windows Computer

Keep these files and folders together in one folder:

```text
asterisk-ivr-deployment/
  deploy-windows.ps1
  key.txt
  client.yml
  audio/
    welcome-open.wav
    welcome-closed.wav
    invalid-option.wav
    timeout.wav
    sales.wav
    support.wav
    voicemail.wav
```

`key.txt` must contain the private SSH key for the server.

`client.yml` contains the phone provider, working hours, voicemail email, and IVR menu settings.

`audio/` contains all audio files referenced by `client.yml`.

## What the Script Does

The script:

1. Reads the private key from `key.txt`.
2. Connects to the Ubuntu server by SSH.
3. Installs Git on the server if Git is missing.
4. Clones this repository from `https://github.com/sptmru/asterisk-ivr-deployment`.
5. Uploads local `client.yml` to the server.
6. Uploads all local files from `audio/` to the server.
7. Runs `./deploy.sh` on the server.
8. Shows the Docker container status.

The server-side `./deploy.sh` installs Docker, Docker Compose, Python YAML support, and ffmpeg if they are missing.

By default, the project is installed on the server at:

```text
/root/asterisk-ivr-deployment
```

If your SSH username is not `root`, the folder will be under that user's home directory instead.

## Before Running

Make sure you have:

- Windows 10 or Windows 11
- PowerShell
- OpenSSH Client installed on Windows
- Server IP address
- SSH username, usually `root`
- `key.txt` in the same folder as `deploy-windows.ps1`
- `client.yml` already filled in
- audio files placed in `audio/`

To check whether OpenSSH is installed, open PowerShell and run:

```powershell
ssh -V
```

If Windows says `ssh` is not recognized, install **OpenSSH Client** from Windows Optional Features.

## Run the Script

Open PowerShell in the project folder.

One easy way:

1. Open the folder in File Explorer.
2. Hold `Shift`.
3. Right-click inside the folder.
4. Choose **Open PowerShell window here** or **Open in Terminal**.

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\deploy-windows.ps1
```

PowerShell will ask for:

- server IP address or hostname
- SSH username

If the username is `root`, press Enter when it shows:

```text
SSH username [root]:
```

You can also provide the server IP directly:

```powershell
.\deploy-windows.ps1 -ServerHost 203.0.113.10
```

Or provide both server IP and username:

```powershell
.\deploy-windows.ps1 -ServerHost 203.0.113.10 -ServerUser root
```

If the project should use a different folder name on the server, run:

```powershell
.\deploy-windows.ps1 -ServerHost 203.0.113.10 -RemoteDir company-ivr
```

## First Run Warning

The first time the script connects to a new server, SSH may ask whether to trust the server.

The script uses `StrictHostKeyChecking=accept-new`, so modern Windows OpenSSH normally accepts a new server automatically.

If Windows still asks:

```text
Are you sure you want to continue connecting?
```

Type:

```text
yes
```

Then press Enter.

## If PowerShell Blocks the Script

If PowerShell says scripts are disabled, run this command from the same folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy-windows.ps1
```

## After It Finishes

If deployment succeeds, the script prints:

```text
Deployment finished.
```

Then call the phone number and test:

- open-hours greeting
- each keypad option
- transfer phone numbers
- voicemail email delivery
- closed-hours voicemail behavior

## Making Changes Later

To change settings:

1. Edit `client.yml` on the Windows computer.
2. Add or replace files in `audio/` if needed.
3. Run `.\deploy-windows.ps1` again.

The script uploads the latest config and audio files, then redeploys the IVR.

## Common Problems

### `key.txt` was not found

Put the private SSH key file in the same folder as `deploy-windows.ps1` and name it exactly:

```text
key.txt
```

### `client.yml` was not found

Create the real config file before running the script:

```text
client.yml
```

Do not rely on `client.example.yml` for real deployment.

### No audio files found

Put the IVR prompt files into:

```text
audio\
```

The filenames must match the names in `client.yml`.

### Permission denied when connecting by SSH

Check:

- `key.txt` contains the correct private key
- the server IP address is correct
- the SSH username is correct
- the public key is installed on the server

### The script asks for a sudo password

This can happen while the server installs Git, Docker, or other packages.

Type the server user's password if you have it. If you do not have it, ask the server administrator to allow this user to run `sudo`.

### Calls connect but there is no audio

Make sure the server firewall and cloud firewall allow:

- UDP `5060`
- UDP `10000-10100`

### Voicemail emails are not arriving

Check the SMTP settings in `config/client.yml`.

To inspect the email log, SSH into the server and run:

```bash
cd ~/asterisk-ivr-deployment
cat runtime/log/msmtp.log
```
