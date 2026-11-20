"""Verify the download registry against the files on disk.

Checks, for every row: file exists, byte size matches, SHA-256 matches and the
file starts with the PDF magic bytes. Also reports leftover .part files and
PDFs that are not registered. Read-only: never modifies the registry.

Usage:
    python src/collect/verify_downloads.py
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/raw/joradp/downloads.sqlite"
PDF_DIR = ROOT / "data/raw/joradp/pdf"


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    if not DB.exists():
        print(f"registre absent : {DB}")
        return 1
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "select k, path, sha256, bytes from downloads order by k"
        ).fetchall()
    finally:
        con.close()

    bad: list[str] = []
    registered: set[Path] = set()
    for k, path, sha, nbytes in rows:
        p = resolve(path)
        registered.add(p.resolve())
        ok = p.exists() and p.stat().st_size == nbytes
        if ok:
            data = p.read_bytes()
            ok = data[:5] == b"%PDF-" and hashlib.sha256(data).hexdigest() == sha
        if not ok:
            bad.append(k)

    parts = list((ROOT / "data/raw/joradp").rglob("*.part"))
    strays = [
        p
        for p in PDF_DIR.rglob("*")
        if p.suffix.lower() == ".pdf" and p.resolve() not in registered
    ]
    print(
        f"{len(rows) - len(bad)}/{len(rows)} conformes | bad={bad} | "
        f".part={len(parts)} | unregistered_pdf={len(strays)}"
    )
    for p in strays:
        print(f"  hors registre : {p.relative_to(ROOT)}")
    return 1 if (bad or parts or strays) else 0


if __name__ == "__main__":
    raise SystemExit(main())
