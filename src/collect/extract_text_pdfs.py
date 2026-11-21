"""Extract text from digitally-typeset PDFs (kind=text in pdf_report).

These PDFs have embedded text — no OCR needed. We call page.get_text()
and write to text_v2/ in the same layout as ocr_columns.py so the
cleaning and extraction pipeline picks them up automatically.

Outputs:
    data/raw/joradp/text_v2/<lang>/<year>/<stem>.txt

Run from the repository root:
    python src/collect/extract_text_pdfs.py
    python src/collect/extract_text_pdfs.py --force
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/joradp"
REPORT = ROOT / "data/processed/pdf_report.csv"
OUT_ROOT = RAW / "text_v2"
MIN_SKIP_BYTES = 2000


def extract_file(lang: str, year: int, file: str, *,
                 out_root: Path = OUT_ROOT, force: bool = False) -> tuple[int, int, str, float]:
    src = RAW / "pdf" / lang / str(year) / file
    dst = out_root / lang / str(year) / (Path(file).stem + ".txt")

    if not force and dst.exists() and dst.stat().st_size >= MIN_SKIP_BYTES:
        return 0, 0, "skipped", 0.0

    t0 = time.time()
    pages_text = []

    with pymupdf.open(src) as doc:
        for page in doc:
            text = page.get_text()
            pages_text.append(text)

    full_text = "\n".join(pages_text)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(full_text, encoding="utf-8")

    return len(pages_text), len(full_text), "extracted", round(time.time() - t0, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from text PDFs")
    parser.add_argument("--force", action="store_true", help="re-extract even if .txt exists")
    parser.add_argument("--lang", choices=["fr", "ar"], help="only this language")
    args = parser.parse_args()

    if not REPORT.exists():
        print(f"missing: {REPORT} — run inspect_pdfs.py first")
        return 1

    df = pd.read_csv(REPORT)
    texts = df[df.kind == "text"]
    if args.lang:
        texts = texts[texts.lang == args.lang]
    if texts.empty:
        print("no text PDF to process")
        return 0

    counts: dict[str, int] = {}
    started = time.time()

    for row in texts.itertuples():
        label = f"{row.lang} {row.year}/{Path(row.file).stem}"
        try:
            pages, chars, status, seconds = extract_file(
                row.lang, row.year, row.file, force=args.force
            )
        except Exception as exc:
            pages, chars, status, seconds = 0, 0, f"failed: {type(exc).__name__}", 0.0
        counts[status] = counts.get(status, 0) + 1
        print(f"{status:16} {label:22} {pages:>3} pages {chars:>8} chars {seconds:>6.1f}s")

    elapsed = time.time() - started
    print(f"\n{counts}")
    print(f"total {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
