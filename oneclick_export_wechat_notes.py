import os
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main():
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    runpy.run_path(str(ROOT / "export-wenote-markdown.py"), run_name="__main__")


if __name__ == "__main__":
    main()
