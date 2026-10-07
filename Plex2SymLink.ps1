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
$symdir = Read-Host "Enter the output path for your symoblic link directory (e.g., C:\JellyfinSymLinks)"

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
    Pause
    exit
}

$key = Read-Host "`nEnter the Library Key for the library you want to export"

# Extract the library title dynamically based on the chosen key
$library_title = ($libs.MediaContainer.Directory | Where-Object { $_.key -eq $key }).title

Write-Host "`nDownloading metadata.xml (this may take a moment for large libraries)..." -ForegroundColor Cyan
$metadata_url = "$plex_ip/library/sections/$key/all?type=4&includeGuids=1&X-Plex-Token=$token"
Invoke-WebRequest -Uri $metadata_url -OutFile "metadata.xml"

Write-Host "`nRunning Symlink Creator (TV_SymLinker.py)..." -ForegroundColor Cyan
# Pass the directory and the library title as arguments to Python
python TV_SymLinker.py "$symdir" "$library_title"

Write-Host "`nAll done! You can now point your Jellyfin TV library at your new symlink root folder." -ForegroundColor Green
Pause