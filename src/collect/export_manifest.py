"""Export the download registry to a portable CSV proof (URLs + hashes).

The SQLite registry is git-ignored (binary, changes often) and stores absolute
paths, so the URL/SHA-256 evidence exists only on one machine. This export
writes a small, reviewable CSV that can be committed: from it, anyone can
re-download the same PDFs and regenerate OCR/text without a shared drive.

Usage:
    python src/collect/export_manifest.py
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/raw/joradp/downloads.sqlite"
OUT = ROOT / "data/processed/downloads_manifest.csv"


def portable(path: str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return path


def main() -> int:
    if not DB.exists():
        print(f"registry absent: {DB}")
        return 1
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "select k, url, sha256, bytes, fetched_at, path, issue, edition "
            "from downloads order by k"
        ).fetchall()
    finally:
        con.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["k", "url", "sha256", "bytes", "fetched_at", "path", "issue", "edition"]
        )
        for k, url, sha, nbytes, when, path, issue, edition in rows:
            w.writerow([k, url, sha, nbytes, when, portable(path), issue, edition])
    print(f"{len(rows)} lignes -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
