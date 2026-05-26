import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "wechat-notes" / "wenote-markdown-localized"
RAW_DIR = ROOT / "wechat-notes" / "raw"
ATTACHMENTS_DIR = OUT_DIR / "attachments"


def safe_filename(text, fallback):
    text = (text or "").strip() or fallback
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return (text[:80].strip() or fallback)


def load_cache_path():
    mtimes = Path(tempfile.gettempdir()) / "wechat_cli_cache" / "_mtimes.json"
    data = json.loads(mtimes.read_text(encoding="utf-8"))
    item = data.get("favorite\\favorite.db") or data.get("favorite/favorite.db")
    if not item:
        raise SystemExit("favorite.db is not in wechat-cli cache. Run favorites first.")
    return Path(item["path"])


def load_wechat_base_dir():
    config_path = Path.home() / ".wechat-cli" / "config.json"
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    db_dir = Path(cfg["db_dir"])
    return db_dir.parent if db_dir.name.lower() == "db_storage" else db_dir


def build_file_index(wechat_base_dir):
    roots = [
        wechat_base_dir / "business" / "favorite" / "temp",
        wechat_base_dir / "business" / "xeditor" / "XEditorBackup" / "Resources",
        wechat_base_dir / "business" / "favorite" / "data",
        wechat_base_dir / "business" / "favorite" / "mid",
        wechat_base_dir / "business" / "favorite" / "thumb",
    ]
    by_name = {}
    by_size = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            by_name.setdefault(path.name.lower(), []).append(path)
            by_size.setdefault(path.stat().st_size, []).append(path)
    return by_name, by_size


def detect_extension(path):
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        return suffix
    try:
        header = path.read_bytes()[:16]
    except OSError:
        return ".bin"
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return ".gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    if header.startswith(b"BM"):
        return ".bmp"
    return ".bin"


def is_real_image(path):
    return detect_extension(path) != ".bin"


def find_attachment(dataid, fullmd5, fullsize, by_name, by_size):
    candidates = []
    for key in [fullmd5, dataid]:
        if key:
            candidates.extend(by_name.get(key.lower(), []))

    try:
        size = int(fullsize) if fullsize else None
    except ValueError:
        size = None
    if size:
        candidates.extend(by_size.get(size, []))

    seen = set()
    unique = []
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    real_images = [path for path in unique if is_real_image(path)]
    if real_images:
        return real_images[0]
    real_images = [path for path in unique if is_real_image(path)]
    if real_images:
        return real_images[0]
    return unique[0] if unique else None


def clear_output_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUT_DIR.glob("*.md"):
        try:
            os.chmod(path, 0o666)
            path.unlink()
        except PermissionError:
            pass
    for path in ATTACHMENTS_DIR.iterdir():
        if path.is_file():
            try:
                os.chmod(path, 0o666)
                path.unlink()
            except PermissionError:
                pass


def copy_attachment(source, target):
    if target.exists():
        os.chmod(target, 0o666)
    shutil.copyfile(source, target)
    os.chmod(target, 0o666)


def prime_wechat_cli_cache():
    wrapper = ROOT / "run-wechat-cli.ps1"
    if not wrapper.exists():
        return
    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(wrapper),
        "favorites",
        "--limit",
        "500",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("wechat-cli favorites failed. Run init first, then retry.")


def parse_note_xml(content, by_name, by_size):
    root = ET.fromstring(content)
    item = root if root.tag == "favitem" else root.find(".//favitem")
    if item is None:
        return "", []

    title = ""
    blocks = []
    image_index = 0

    for dataitem in item.findall(".//dataitem"):
        datatype = dataitem.get("datatype")
        desc = html.unescape((dataitem.findtext("datadesc") or "").strip())
        datatitle = html.unescape((dataitem.findtext("datatitle") or "").strip())

        if datatype == "1":
            if desc:
                blocks.append(desc.replace("\r\n", "\n").replace("\r", "\n"))
                if not title:
                    first_line = next((line.strip() for line in desc.splitlines() if line.strip()), "")
                    title = first_line
        elif datatype == "2":
            image_index += 1
            dataid = dataitem.get("dataid", "")
            fullmd5 = dataitem.findtext("fullmd5") or ""
            fullsize = dataitem.findtext("fullsize") or ""
            source = find_attachment(dataid, fullmd5, fullsize, by_name, by_size)
            if source:
                ext = detect_extension(source)
                target_name = f"{fullmd5 or dataid}{ext}"
                target = ATTACHMENTS_DIR / target_name
                copy_attachment(source, target)
                blocks.append(f"![微信收藏图片 {image_index}](attachments/{target_name})")
                blocks.append(f"<!-- image source={source} dataid={dataid} fullmd5={fullmd5} fullsize={fullsize} -->")
            else:
                blocks.append(f"![微信收藏图片 {image_index}](attachments/{dataid}.jpg)")
                blocks.append(f"<!-- missing image dataid={dataid} fullmd5={fullmd5} fullsize={fullsize} -->")
        elif desc or datatitle:
            blocks.append("\n".join(part for part in [datatitle, desc] if part))

    return title, blocks


def main():
    prime_wechat_cli_cache()
    clear_output_dir()

    db_path = load_cache_path()
    wechat_base_dir = load_wechat_base_dir()
    by_name, by_size = build_file_index(wechat_base_dir)
    con = sqlite3.connect(db_path)
    rows = con.execute(
        """
        SELECT local_id, type, update_time, content, fromusr, realchatname
        FROM fav_db_item
        WHERE type = 18
        ORDER BY update_time DESC, local_id DESC
        """
    ).fetchall()

    manifest = []
    for index, (local_id, typ, ts, content, fromusr, realchatname) in enumerate(rows, 1):
        try:
            title, blocks = parse_note_xml(content or "", by_name, by_size)
        except ET.ParseError:
            title, blocks = "", [content or ""]

        created = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        fallback = f"wechat-note-{local_id}"
        file_title = safe_filename(title, fallback)
        path = OUT_DIR / f"{index:04d}-{file_title}.md"

        body = "\n\n".join(block for block in blocks if block.strip()).strip()
        md = [
            "---",
            "source: wechat",
            "kind: wenote",
            f"id: {local_id}",
            f"type: {typ}",
            f'created: "{created}"',
            f'from: "{fromusr or ""}"',
            f'source_chat: "{realchatname or ""}"',
            "---",
            "",
            f"# {file_title}",
            "",
            body,
            "",
        ]
        path.write_text("\n".join(md), encoding="utf-8")
        manifest.append({"id": local_id, "time": created, "file": str(path)})

    (RAW_DIR / "wenote-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {len(rows)} WeNote markdown files to {OUT_DIR}")


if __name__ == "__main__":
    main()
