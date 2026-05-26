param(
    [string]$OutputDir = ".\wechat-notes",
    [string]$WechatCli = ".\run-wechat-cli.ps1",
    [switch]$SkipExport
)

$ErrorActionPreference = "Stop"

function New-SafeFileName {
    param(
        [string]$Name,
        [string]$Fallback
    )

    if ([string]::IsNullOrWhiteSpace($Name)) {
        $Name = $Fallback
    }

    $invalid = [System.IO.Path]::GetInvalidFileNameChars()
    foreach ($char in $invalid) {
        $Name = $Name.Replace($char, "-")
    }

    $Name = ($Name -replace "\s+", " ").Trim()
    if ($Name.Length -gt 80) {
        $Name = $Name.Substring(0, 80).Trim()
    }

    if ([string]::IsNullOrWhiteSpace($Name)) {
        return $Fallback
    }

    return $Name
}

function ConvertTo-MarkdownText {
    param($Value)

    if ($null -eq $Value) {
        return ""
    }

    if ($Value -is [string]) {
        return $Value.Trim()
    }

    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        $parts = @()
        foreach ($item in $Value) {
            $parts += ConvertTo-MarkdownText $item
        }
        return (($parts | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n`n").Trim()
    }

    $json = $Value | ConvertTo-Json -Depth 20
    $fence = [string][char]96 + [string][char]96 + [string][char]96
    return ($fence + "json" + "`n" + $json + "`n" + $fence)
}

function Get-FirstProperty {
    param(
        $Object,
        [string[]]$Names
    )

    if ($null -eq $Object) {
        return $null
    }

    $props = $Object.PSObject.Properties
    foreach ($name in $Names) {
        $prop = $props[$name]
        if ($null -ne $prop -and $null -ne $prop.Value -and ([string]$prop.Value).Trim() -ne "") {
            return $prop.Value
        }
    }

    return $null
}

function Get-NoteItems {
    param($Json)

    if ($Json -is [System.Collections.IEnumerable] -and $Json -isnot [string] -and $Json -isnot [pscustomobject]) {
        return ,$Json
    }

    foreach ($name in @("favorites", "items", "data", "list", "records", "result")) {
        $value = Get-FirstProperty $Json @($name)
        if ($value -is [System.Collections.IEnumerable] -and $value -isnot [string]) {
            return ,$value
        }
    }

    return @($Json)
}

$root = Resolve-Path "."
$outPath = Join-Path $root $OutputDir
$rawPath = Join-Path $outPath "raw"
$mdPath = Join-Path $outPath "markdown"
$rawJsonPath = Join-Path $rawPath "favorites.json"

New-Item -ItemType Directory -Force -Path $rawPath, $mdPath | Out-Null

if (-not $SkipExport) {
    Write-Host "Checking wechat-cli..."
    $cmd = Get-Command $WechatCli -ErrorAction SilentlyContinue
    if ($null -eq $cmd -and -not (Test-Path -LiteralPath $WechatCli)) {
        throw "Cannot find '$WechatCli'. Install it first, or pass -WechatCli with the full executable path."
    }

    Write-Host "Exporting WeChat favorites/notes to $rawJsonPath ..."
    & $WechatCli favorites | Out-File -FilePath $rawJsonPath -Encoding utf8
}
elseif (-not (Test-Path -LiteralPath $rawJsonPath)) {
    throw "SkipExport was set, but raw JSON does not exist: $rawJsonPath"
}

Write-Host "Reading $rawJsonPath ..."
$raw = Get-Content -LiteralPath $rawJsonPath -Raw -Encoding utf8
if ([string]::IsNullOrWhiteSpace($raw)) {
    throw "Exported JSON is empty: $rawJsonPath"
}

$json = $raw | ConvertFrom-Json
if ($null -ne $json.favorites) {
    $items = @($json.favorites)
}
elseif ($null -ne $json.items) {
    $items = @($json.items)
}
elseif ($null -ne $json.data) {
    $items = @($json.data)
}
elseif ($null -ne $json.list) {
    $items = @($json.list)
}
elseif ($null -ne $json.records) {
    $items = @($json.records)
}
elseif ($null -ne $json.result) {
    $items = @($json.result)
}
else {
    $items = @($json)
}

if ($items.Count -eq 0) {
    throw "No note/favorite items found in exported JSON."
}

$index = 0
foreach ($item in $items) {
    $index += 1

    $title = Get-FirstProperty $item @("title", "name", "desc", "description", "summary")
    $content = Get-FirstProperty $item @("content", "text", "html", "note", "body", "data")
    $created = Get-FirstProperty $item @("createTime", "createdTime", "created_at", "time", "timestamp", "date")
    $source = Get-FirstProperty $item @("source", "from", "sender", "user", "author")
    $url = Get-FirstProperty $item @("url", "link")

    $fallbackTitle = "wechat-note-{0:D4}" -f $index
    $safeTitle = New-SafeFileName -Name "$title" -Fallback $fallbackTitle
    $fileName = "{0:D4}-{1}.md" -f $index, $safeTitle
    $filePath = Join-Path $mdPath $fileName

    $markdownBody = ConvertTo-MarkdownText $content
    if ([string]::IsNullOrWhiteSpace($markdownBody)) {
        $markdownBody = ConvertTo-MarkdownText $item
    }

    $frontMatter = @(
        "---"
        "source: wechat"
        "kind: favorite-note"
        "index: $index"
    )

    if ($title) {
        $escapedTitle = "$title".Replace('"', '\"')
        $frontMatter += "title: `"$escapedTitle`""
    }
    if ($created) {
        $frontMatter += "created: `"$created`""
    }
    if ($source) {
        $escapedSource = "$source".Replace('"', '\"')
        $frontMatter += "wechat_source: `"$escapedSource`""
    }
    if ($url) {
        $frontMatter += "url: `"$url`""
    }
    $frontMatter += "---"

    $md = @()
    $md += $frontMatter
    $md += ""
    $md += "# $safeTitle"
    $md += ""
    $md += $markdownBody
    $md += ""

    Set-Content -LiteralPath $filePath -Value ($md -join "`n") -Encoding utf8
}

Write-Host "Done."
Write-Host "Raw JSON: $rawJsonPath"
Write-Host "Markdown files: $mdPath"
Write-Host "Files written: $($items.Count)"
