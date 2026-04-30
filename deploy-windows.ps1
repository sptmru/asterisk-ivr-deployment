param(
    [string]$ServerHost,
    [string]$ServerUser = "ubuntu",
    [string]$RemoteDir = "asterisk-ivr-deployment",
    [string]$RepoUrl = "https://github.com/sptmru/asterisk-ivr-deployment.git"
)

$ErrorActionPreference = "Stop"

function Fail($Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Run-Command($Command, $Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        Fail "$Command failed with exit code $LASTEXITCODE"
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KeyPath = Join-Path $ScriptDir "key.txt"
$ConfigPath = Join-Path $ScriptDir "client.yml"
$AudioDir = Join-Path $ScriptDir "audio"

if (-not $ServerHost) {
    $ServerHost = Read-Host "Server IP address or hostname"
}

if (-not $ServerHost) {
    Fail "Server IP address or hostname is required."
}

$InputUser = Read-Host "SSH username [$ServerUser]"
if ($InputUser) {
    $ServerUser = $InputUser
}

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Fail "ssh was not found. Install OpenSSH Client from Windows Optional Features, then run this script again."
}

if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Fail "scp was not found. Install OpenSSH Client from Windows Optional Features, then run this script again."
}

if (-not (Test-Path $KeyPath)) {
    Fail "Private key file not found: $KeyPath. Put the SSH private key in key.txt beside this script."
}

if (-not (Test-Path $ConfigPath)) {
    Fail "Config file not found: $ConfigPath. Create client.yml before running this script."
}

if (-not (Test-Path $AudioDir)) {
    Fail "Audio folder not found: $AudioDir"
}

$AudioFiles = Get-ChildItem -Path $AudioDir -File | Where-Object { $_.Name -ne ".gitkeep" }
if ($AudioFiles.Count -eq 0) {
    Fail "No audio files found in $AudioDir. Put the IVR prompt files there before running this script."
}

if ($RemoteDir -match '(^/|^~|(^|/)\.\.($|/))') {
    Fail "RemoteDir must be a folder name under the SSH user's home directory, for example: asterisk-ivr-deployment"
}

$SshTarget = "$ServerUser@$ServerHost"
$SshBaseArgs = @(
    "-i", $KeyPath,
    "-o", "IdentitiesOnly=yes",
    "-o", "StrictHostKeyChecking=accept-new"
)

if ($env:OS -eq "Windows_NT" -and (Get-Command icacls -ErrorAction SilentlyContinue)) {
    Step "Securing key.txt permissions for Windows OpenSSH"
    & icacls $KeyPath /inheritance:r /grant:r "$($env:USERNAME):R" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Could not update key.txt permissions automatically. Continuing anyway." -ForegroundColor Yellow
    }
}

Step "Testing SSH connection to $SshTarget"
Run-Command "ssh" ($SshBaseArgs + @($SshTarget, "echo SSH connection OK"))

$RemoteHome = (& ssh @SshBaseArgs $SshTarget 'printf %s "$HOME"')
if ($LASTEXITCODE -ne 0 -or -not $RemoteHome) {
    Fail "Could not determine the server home directory."
}
$RemoteHome = $RemoteHome.Trim()
$RemotePath = "$RemoteHome/$RemoteDir"

$RemoteSetup = @"
set -e
if ! command -v git >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y git
fi
if [ ! -e "$RemotePath" ]; then
  git clone "$RepoUrl" "$RemotePath"
elif [ -d "$RemotePath/.git" ]; then
  cd "$RemotePath"
  git pull --ff-only
else
  echo "Remote path exists but is not a Git checkout: $RemotePath" >&2
  exit 1
fi
mkdir -p "$RemotePath/config" "$RemotePath/audio"
"@

Step "Preparing project on the Ubuntu server"
Run-Command "ssh" ($SshBaseArgs + @("-tt", $SshTarget, $RemoteSetup))

Step "Uploading config\client.yml"
$RemoteConfigTarget = "${SshTarget}:$RemotePath/config/client.yml"
Run-Command "scp" ($SshBaseArgs + @($ConfigPath, $RemoteConfigTarget))

Step "Uploading audio files"
$RemoteAudioTarget = "${SshTarget}:$RemotePath/audio/"
foreach ($AudioFile in $AudioFiles) {
    Write-Host "Uploading $($AudioFile.Name)"
    Run-Command "scp" ($SshBaseArgs + @($AudioFile.FullName, $RemoteAudioTarget))
}

$RemoteDeploy = @"
set -e
cd "$RemotePath"
chmod +x deploy.sh install-ubuntu.sh
./deploy.sh
"@

Step "Running deployment on the server"
Run-Command "ssh" ($SshBaseArgs + @("-tt", $SshTarget, $RemoteDeploy))

Step "Checking running containers"
Run-Command "ssh" ($SshBaseArgs + @($SshTarget, "cd `"$RemotePath`" && docker compose ps"))

Write-Host ""
Write-Host "Deployment finished." -ForegroundColor Green
Write-Host "To watch server logs later, run:"
Write-Host "ssh -i key.txt $SshTarget"
Write-Host "cd $RemotePath"
Write-Host "docker compose logs -f asterisk"
