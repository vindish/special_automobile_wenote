param(
    [switch]$PauseOnExit
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Invoke-Exporter {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        & $python.Source ".\oneclick_export_wechat_notes.py"
        $script:ExporterExitCode = $LASTEXITCODE
        return
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        & $py.Source -3 ".\oneclick_export_wechat_notes.py"
        $script:ExporterExitCode = $LASTEXITCODE
        return
    }

    throw "Python was not found. Install Python or add it to PATH."
}

try {
    $script:ExporterExitCode = 1
    Invoke-Exporter
    if ($script:ExporterExitCode -ne 0) {
        throw "Exporter exited with code $script:ExporterExitCode."
    }

    Write-Host ""
    Write-Host "Done."
    Write-Host "Markdown output: $scriptDir\wechat-notes\wenote-markdown-localized"
}
catch {
    Write-Host ""
    Write-Host "Export failed:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if (-not $PauseOnExit) {
        exit 1
    }
}

if ($PauseOnExit) {
    Write-Host ""
    Read-Host "Press Enter to close"
}
