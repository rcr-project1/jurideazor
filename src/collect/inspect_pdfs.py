"""Classify every downloaded PDF page as text or scan.

A page counts as "scan" when its extracted text is shorter than 50 characters.
The file kind is text (no scan page), scan (no text page) or mixed. Writes
data/processed/pdf_report.csv with per-file page counts.

Usage:
    python src/collect/inspect_pdfs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/joradp/pdf"
OUT = ROOT / "data/processed/pdf_report.csv"
TEXT_MIN_CHARS = 50


def classify(pdf: Path) -> dict:
    lang = pdf.parts[-3]
    year = int(pdf.parts[-2])
    doc = pymupdf.open(pdf)
    try:
        pages = doc.page_count
        chars = 0
        scan_pages = 0
        for page in doc:
            n = len(page.get_text().strip())
            chars += n
            if n < TEXT_MIN_CHARS:
                scan_pages += 1
    finally:
        doc.close()
    if scan_pages == 0:
        kind = "text"
    elif scan_pages == pages:
        kind = "scan"
    else:
        kind = "mixed"
    return {
        "lang": lang,
        "year": year,
        "file": pdf.name,
        "pages": pages,
        "chars": chars,
        "pages_text": pages - scan_pages,
        "pages_scan": scan_pages,
        "kind": kind,
    }


def main() -> int:
    rows: list[dict] = []
    errors = 0
    for pdf in sorted(RAW.rglob("*")):
        if pdf.suffix.lower() != ".pdf":
            continue
        try:
            rows.append(classify(pdf))
        except Exception as exc:  # noqa: BLE001 - reported as a row
            errors += 1
            rows.append(
                {
                    "lang": pdf.parts[-3],
                    "year": int(pdf.parts[-2]),
                    "file": pdf.name,
                    "pages": 0,
                    "chars": 0,
                    "pages_text": 0,
                    "pages_scan": 0,
                    "kind": f"ERROR: {type(exc).__name__}",
                }
            )
    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(out.to_string(index=False))
    print(f"\n{len(rows)} PDF, {errors} erreur(s) -> {OUT.relative_to(ROOT)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
