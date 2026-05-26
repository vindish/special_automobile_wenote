param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WechatCliArgs
)

$ErrorActionPreference = "Stop"

$userSite = Join-Path $env:APPDATA "Python\Python311\site-packages"
$scriptPath = Join-Path $env:APPDATA "Python\Python311\Scripts\wechat-cli.exe"

if (-not (Test-Path -LiteralPath $userSite)) {
    throw "Python user site-packages not found: $userSite"
}

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "wechat-cli.exe not found: $scriptPath"
}

$env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $userSite
}
else {
    "$userSite;$env:PYTHONPATH"
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

& $scriptPath @WechatCliArgs
exit $LASTEXITCODE
