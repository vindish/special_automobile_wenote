# WeChat Notes Export

This folder contains a Windows PowerShell script for batch-exporting WeChat built-in favorites/notes to Markdown.

## Prerequisites

1. Install and log in to Windows WeChat.
2. Install `wechat-cli`.
3. Run its initialization once if needed:

```powershell
wechat-cli init
```

## Export Notes

Run from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\export.ps1
```

Output:

- `wechat-notes/raw/wenote-manifest.json`: export manifest
- `wechat-notes/wenote-markdown-localized/*.md`: one Markdown file per note
- `wechat-notes/wenote-markdown-localized/attachments/*`: local image files

## Convert Existing JSON Only

If you already have the cache and want to rerun only the exporter:

```powershell
powershell -ExecutionPolicy Bypass -File .\export.ps1
```

## Custom Output Directory

```powershell
powershell -ExecutionPolicy Bypass -File .\export.ps1
```

## Troubleshooting

The exporter refreshes the local `wechat-cli` cache automatically by calling the wrapper script. If that step fails, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-wechat-cli.ps1 favorites
```
# special_automobile_wenote
