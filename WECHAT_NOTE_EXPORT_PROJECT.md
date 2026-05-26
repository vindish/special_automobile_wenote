# WeChat Note Export Project

## Goal

Export WeChat built-in favorites/notes from the local Windows machine into Markdown files, with images copied to local attachments.

## What Was Installed

- `@canghe_ai/wechat-cli` via npm, but it was deprecated and missing Windows binary support.
- Python source version of `wechat-cli` from GitHub, installed in the user Python environment.

## Working Setup

1. Initialize WeChat CLI once:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-wechat-cli.ps1 init
```

2. Export notes:

```powershell
powershell -ExecutionPolicy Bypass -File .\export.ps1
```

## Output

- `wechat-notes/wenote-markdown-localized/*.md`
- `wechat-notes/wenote-markdown-localized/attachments/*`
- `wechat-notes/raw/wenote-manifest.json`

## Key Fixes

### 1. Recover note body from local SQLite

The `favorites` command only returns summaries. The actual note content lives in the decrypted local `favorite.db` under `fav_db_item.content`.

### 2. Localize images

Image entries in the XML are resolved against local WeChat data directories:

- `business/favorite/temp`
- `business/xeditor/XEditorBackup/Resources`
- `business/favorite/data`
- `business/favorite/mid`
- `business/favorite/thumb`

The exporter copies matched files into the Markdown attachment folder and rewrites links to local relative paths.

### 3. Eliminate `.bin` attachments

Some files were copied with `.bin` because extension detection fell back too early. The exporter now prefers real image files and copies only image-like sources.

### 4. Make the exporter repeatable

The exporter now:

- refreshes the `wechat-cli` cache before export
- clears the output directory
- copies attachments with writable permissions
- avoids stale output from previous runs

## Final One-Click Command

```powershell
powershell -ExecutionPolicy Bypass -File .\export.ps1
```

## Notes

If the cache is missing, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-wechat-cli.ps1 favorites
```

If WeChat changes its local file layout later, adjust the attachment search roots in `export-wenote-markdown.py`.
