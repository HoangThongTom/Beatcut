param(
    [ValidateRange(60, 86400)]
    [int]$MaxDurationSeconds = 3600,
    [ValidateRange(1024, 65535)]
    [int]$Port = 8501,
    [switch]$NoBrowser,
    [switch]$Annotate
)

$ErrorActionPreference = 'Stop'
if ($Annotate -and -not $PSBoundParameters.ContainsKey('Port')) { $Port = 8503 }
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Run .\scripts\bootstrap.ps1 first, then install requirements.txt in .venv.'
}

foreach ($binary in @('ffmpeg', 'ffprobe')) {
    $envName = if ($binary -eq 'ffmpeg') { 'FFMPEG_BIN' } else { 'FFPROBE_BIN' }
    if (-not [Environment]::GetEnvironmentVariable($envName, 'Process')) {
        $portable = Join-Path $projectRoot "tools\ffmpeg\$binary.exe"
        if (Test-Path -LiteralPath $portable) {
            [Environment]::SetEnvironmentVariable($envName, $portable, 'Process')
        }
        elseif (-not (Get-Command $binary -ErrorAction SilentlyContinue)) {
            throw "Install FFmpeg or place $binary.exe in tools\ffmpeg."
        }
    }
}

$env:BEATCUT_LOCAL = '1'
$env:BEATCUT_MAX_DURATION_S = [string]$MaxDurationSeconds
Push-Location $projectRoot
try {
    & $python -c 'import streamlit, beatcut'
    if ($LASTEXITCODE -ne 0) {
        throw 'Missing dependencies. Run .\.venv\Scripts\python.exe -m pip install -r requirements.txt -e .'
    }
    Write-Host "BeatCut local: http://localhost:$Port" -ForegroundColor Cyan
    Write-Host "Gameplay limit: $MaxDurationSeconds seconds. Upload limit: 1024 MB per file."
    Write-Host 'Keep this window open. Press Ctrl+C to stop BeatCut.'
    $headless = if ($NoBrowser) { 'true' } else { 'false' }
    $entryPoint = if ($Annotate) { 'app/labeling_app.py' } else { 'app/streamlit_app.py' }
    & $python -m streamlit run $entryPoint `
        --server.address 127.0.0.1 --server.port $Port `
        --server.maxUploadSize 1024 --server.headless $headless `
        --browser.gatherUsageStats false
    if ($LASTEXITCODE -ne 0) { throw "BeatCut stopped with exit code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
