# --- Plex to Jellyfin NFO Orchestrator ---

# Safely establish the working directory
$working_dir = $PSScriptRoot
if ([string]::IsNullOrEmpty($working_dir)) {
    $working_dir = (Get-Location).Path
}
Set-Location $working_dir

Write-Host "Checking prerequisites..." -ForegroundColor Cyan

# 1. Check if Python is installed and in the system PATH
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is not installed or not added to your system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3 from python.org (ensure 'Add Python to PATH' is checked) and try again." -ForegroundColor Yellow
    Pause
    exit
}

# 2. Check if the required Python scripts exist in the working directory
$missingFiles = $false
if (!(Test-Path "PlexXMLPull.py")) {
    Write-Host "Error: PlexXMLPull.py is missing from $working_dir" -ForegroundColor Red
    $missingFiles = $true
}
if (!(Test-Path "JellyfinNFOCreator.py")) {
    Write-Host "Error: JellyfinNFOCreator.py is missing from $working_dir" -ForegroundColor Red
    $missingFiles = $true
}
if ($missingFiles) {
    Write-Host "Please ensure all required scripts are extracted to the same folder before running." -ForegroundColor Yellow
    Pause
    exit
}

Write-Host "Prerequisites met.`n" -ForegroundColor Green

# Prompt for the variables dynamically at runtime
$plex_ip = Read-Host "Enter your Plex Server URL (e.g., http://192.168.1.50:32400)"
$token = Read-Host "Enter your Plex Token - 'Get Info' on any media item > View XML. The token is at the end of the URL"

# Safely establish the working directory (handles both saved .ps1 files and copy/paste)
$working_dir = $PSScriptRoot
if ([string]::IsNullOrEmpty($working_dir)) {
    $working_dir = (Get-Location).Path
}
Set-Location $working_dir

Write-Host "`nFetching Plex libraries..." -ForegroundColor Cyan
$libraries_url = "$plex_ip/library/sections?X-Plex-Token=$token"

try {
    # Fetch and parse the libraries XML
    [xml]$libs = Invoke-RestMethod -Uri $libraries_url
    Write-Host "`nAvailable Movie Libraries:" -ForegroundColor Yellow
    foreach ($dir in $libs.MediaContainer.Directory) {
        # Filter out TV shows and Music to prevent formatting errors
        if ($dir.type -eq "movie") {
            Write-Host "  Key: $($dir.key) - $($dir.title)"
        }
    }
}
catch {
    Write-Host "Failed to connect to Plex. Double-check your IP and Token." -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Red
    Pause
    exit
}

# Interactive prompt for the key
$key = Read-Host "`nEnter the Library Key for the library you want to export"

Write-Host "`nDownloading metadata.xml (this may take a moment for large libraries)..." -ForegroundColor Cyan
$metadata_url = "$plex_ip/library/sections/$key/all?includeGuids=1&X-Plex-Token=$token"
Invoke-WebRequest -Uri $metadata_url -OutFile "metadata.xml"

Write-Host "`nRunning Audit Script (PlexXMLPull.py)..." -ForegroundColor Cyan
python PlexXMLPull.py

Write-Host "`nAudit complete. Please check audit_log.txt in your folder to confirm the data looks correct." -ForegroundColor Yellow
$continue = Read-Host "Does the audit log look good? (Y/N)"

if ($continue -match "^[yY]") {
    Write-Host "`nRunning NFO Creator (JellyfinNFOCreator.py)..." -ForegroundColor Cyan
    python JellyfinNFOCreator.py
    Write-Host "`nAll done! You can now run a 'Scan All Libraries' with 'Replace all metadata' in Jellyfin." -ForegroundColor Green
}
else {
    Write-Host "`nHalting script so you can investigate the audit log." -ForegroundColor Red
}

Pause