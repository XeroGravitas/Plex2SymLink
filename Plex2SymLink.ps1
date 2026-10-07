# --- Plex to Jellyfin TV Symlink Orchestrator ---

# Safely establish the working directory
$working_dir = $PSScriptRoot
if ([string]::IsNullOrEmpty($working_dir)) {
    $working_dir = (Get-Location).Path
}
Set-Location $working_dir

Write-Host "Checking prerequisites..." -ForegroundColor Cyan

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is not installed or not added to your system PATH." -ForegroundColor Red
    Pause
    exit
}

if (!(Test-Path "TV_SymLinker.py")) {
    Write-Host "Error: TV_SymLinker.py is missing from $working_dir" -ForegroundColor Red
    Pause
    exit
}

Write-Host "Prerequisites met.`n" -ForegroundColor Green

# Prompt for the variables dynamically at runtime
$plex_ip = Read-Host "Enter your Plex Server URL (e.g., http://192.168.1.50:32400)"
$token = Read-Host "Enter your Plex Token - 'Get Info' on any media item > View XML. The token is at the end of the URL"
$symdir = Read-Host "Enter the output path for your symbolic link directory (e.g., C:\JellyfinSymLinks)"

Write-Host "`nFetching Plex libraries..." -ForegroundColor Cyan
$libraries_url = "$plex_ip/library/sections?X-Plex-Token=$token"

try {
    [xml]$libs = Invoke-RestMethod -Uri $libraries_url
    Write-Host "`nAvailable TV Libraries:" -ForegroundColor Yellow
    foreach ($dir in $libs.MediaContainer.Directory) {
        if ($dir.type -eq "show") {
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

$key = Read-Host "`nEnter the Library Key for the library you want to export"

# Extract the library title dynamically based on the chosen key
$library_title = ($libs.MediaContainer.Directory | Where-Object { $_.key -eq $key }).title

if ([string]::IsNullOrEmpty($library_title)) {
    Write-Host "Invalid Key entered. Cannot determine library title." -ForegroundColor Red
    Pause
    exit
}

Write-Host "`nDownloading metadata.xml (this may take a moment for large libraries)..." -ForegroundColor Cyan
$metadata_url = "$plex_ip/library/sections/$key/all?type=4&includeGuids=1&X-Plex-Token=$token"

try {
    # -UseBasicParsing is absolutely critical here for massive XML files
    Invoke-WebRequest -Uri $metadata_url -OutFile "metadata.xml" -UseBasicParsing
}
catch {
    Write-Host "Failed to download metadata.xml. The library might be too large or the connection timed out." -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Red
    Pause
    exit
}

Write-Host "`nGenerating Audit Log (symlink_tree.txt)..." -ForegroundColor Cyan

try {
    # Run in audit mode first
    python TV_SymLinker.py "$symdir" "$library_title" "audit"
}
catch {
    Write-Host "Python script encountered an error during the audit phase." -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Red
    Pause
    exit
}

Write-Host "`nAudit complete. Please check symlink_tree.txt in your folder to confirm the routing looks correct." -ForegroundColor Yellow
$continue = Read-Host "Does the audit log look good? (Y/N)"

if ($continue -match "^[yY]") {
    Write-Host "`nBuilding Symlinks..." -ForegroundColor Cyan
    try {
        # Run in execute mode
        python TV_SymLinker.py "$symdir" "$library_title" "execute"
        Write-Host "`nAll done! You can now point your Jellyfin TV library at your new symlink root folder." -ForegroundColor Green
    }
    catch {
        Write-Host "Python script encountered an error during execution." -ForegroundColor Red
        Write-Host "Error details: $_" -ForegroundColor Red
    }
}
else {
    Write-Host "`nHalting script so you can investigate the audit log." -ForegroundColor Red
}

Pause