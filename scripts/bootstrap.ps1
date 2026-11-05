<#
Creates .venv and installs BeatCut in editable mode.

Why Python 3.11: librosa pulls in numba, which does not ship wheels for 3.13+
yet, and PyTorch trails new CPython releases by a few months. 3.11 is the
boring, working choice for this project.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Test-Path '.venv')) {
        Write-Host 'Creating .venv with Python 3.11 ...'
        if (Get-Command py -ErrorAction SilentlyContinue) {
            py -3.11 -m venv .venv
        }
        else {
            python -m venv .venv
        }
    }
    else {
        Write-Host '.venv already exists, reusing it'
    }

    $python = Join-Path $root '.venv\Scripts\python.exe'

    # A fresh venv ships an old pip/setuptools without bdist_wheel, and the
    # editable build then fails with "invalid command 'bdist_wheel'".
    # Upgrade the build toolchain before touching the project.
    & $python -m pip install --upgrade pip setuptools wheel
    & $python -m pip install -e '.[dev]'

    Write-Host ''
    Write-Host 'Installed. Next steps:' -ForegroundColor Green
    Write-Host '  .\.venv\Scripts\Activate.ps1'
    Write-Host '  beatcut doctor'
    Write-Host ''
    Write-Host 'ffmpeg is NOT installed by this script. Install it once with:' -ForegroundColor Yellow
    Write-Host '  winget install Gyan.FFmpeg'
}
finally {
    Pop-Location
}
