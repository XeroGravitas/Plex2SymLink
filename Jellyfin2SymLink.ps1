# --- Jellyfin TV Symlink Orchestrator ---

$working_dir = $PSScriptRoot
if ([string]::IsNullOrEmpty($working_dir)) {
    $working_dir = (Get-Location).Path
}
Set-Location $working_dir

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is not installed or not on PATH." -ForegroundColor Red
    Pause
    exit
}

if (!(Test-Path "Jellyfin_TV_SymLinker.py")) {
    Write-Host "Error: Jellyfin_TV_SymLinker.py is missing from $working_dir" -ForegroundColor Red
    Pause
    exit
}

$jellyfin_url = (Read-Host "Enter your Jellyfin Server URL (e.g., http://192.168.1.50:8096)").Trim()
$symdir = Read-Host "Enter the output path for your symbolic link directory (e.g., C:\JellyfinSymLinks)"
$base_url = $jellyfin_url.TrimEnd('/')
$api_key = (Read-Host "Enter your Jellyfin API key").Trim().Trim('"').Trim("'").Trim()
if ([string]::IsNullOrWhiteSpace($api_key)) {
    Write-Host "Error: The Jellyfin API key cannot be empty." -ForegroundColor Red
    Pause
    exit
}

$client_authorization = 'MediaBrowser Client="Jellyfin2SymLink", Device="PowerShell", DeviceId="Jellyfin2SymLink", Version="1.0"'
$authorization = $client_authorization + ', Token="' + $api_key + '"'
$headers = @{
    "Authorization" = $authorization
    "User-Agent"    = "Jellyfin2SymLink/1.0"
}
$auth_query = "ApiKey=$([uri]::EscapeDataString($api_key))"

try {
    $library_id = $null
    try {
        $libraries_response = Invoke-RestMethod -Uri "$base_url/Library/VirtualFolders?$auth_query" -Headers $headers
        $libraries = @($libraries_response | Where-Object { $_.CollectionType -eq "tvshows" })
        if ($libraries.Count -eq 0) {
            throw "No Jellyfin TV libraries were found."
        }

        Write-Host "`nAvailable TV Libraries:" -ForegroundColor Yellow
        for ($index = 0; $index -lt $libraries.Count; $index++) {
            Write-Host "  $($index + 1): $($libraries[$index].Name)"
        }
        $selection = [int](Read-Host "`nSelect a library number") - 1
        if ($selection -lt 0 -or $selection -ge $libraries.Count) {
            throw "Invalid library selection."
        }
        $library = $libraries[$selection]
        $library_id = $library.ItemId
    }
    catch {
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode -eq 401) {
            Write-Host "The API key cannot enumerate virtual folders on this Jellyfin server." -ForegroundColor Yellow
            Write-Host "Falling back to all matched TV episodes visible to this API key." -ForegroundColor Yellow
            $library_name = Read-Host "Enter the name for the repaired output library"
            $library = @{ Name = $library_name }
        }
        else {
            throw
        }
    }

    Write-Host "`nFetching matched Jellyfin episodes..." -ForegroundColor Cyan
    $episodes = @()
    $start_index = 0
    $page_size = 1000
    do {
        $parent_query = if ($library_id) { "ParentId=$library_id&" } else { "" }
        $items_url = "$base_url/Items?${auth_query}&${parent_query}IncludeItemTypes=Episode&Recursive=true&Fields=Path,SeriesName,ParentIndexNumber,IndexNumber&StartIndex=$start_index&Limit=$page_size"
        $page = Invoke-RestMethod -Uri $items_url -Headers $headers
        $episodes += @($page.Items)
        $start_index += @($page.Items).Count
    } while ($start_index -lt [int]$page.TotalRecordCount -and @($page.Items).Count -gt 0)

    $episodes | ConvertTo-Json -Depth 6 | Set-Content -Path "jellyfin_metadata.json" -Encoding UTF8
}
catch {
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode -eq 401) {
        Write-Host "Jellyfin rejected the API key (HTTP 401). Confirm that the key was created on this Jellyfin server and copied without extra characters." -ForegroundColor Red
    }
    else {
        Write-Host "Failed to fetch Jellyfin library metadata." -ForegroundColor Red
    }
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
    Pause
    exit
}

python Jellyfin_TV_SymLinker.py "$symdir" "$($library.Name)" "audit"
Write-Host "`nAudit complete. Review jellyfin_symlink_tree.txt before continuing." -ForegroundColor Yellow
$continue = Read-Host "Does the audit log look good? (Y/N)"

if ($continue -match "^[yY]") {
    python Jellyfin_TV_SymLinker.py "$symdir" "$($library.Name)" "execute"
    Write-Host "`nDone. Point a new Jellyfin TV library at the generated symlink root." -ForegroundColor Green
}
else {
    Write-Host "`nHalting without creating or changing links." -ForegroundColor Red
}

Pause