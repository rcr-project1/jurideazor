"""OCR with column-aware reading order (v2).

v1 (ocr.py) forced `--psm 4` (single block of text) on two-column pages: Tesseract
read straight across the gutter and interleaved the two columns, which makes the
text impossible to split into articles.

v2 keeps a normal segmentation (`--psm 3`), then rebuilds the reading order from
the block coordinates: full-width header, left column top-to-bottom, right column
top-to-bottom, footer.

Outputs (v1 files are never touched):
    data/raw/joradp/text_v2/<lang>/<year>/<stem>.txt
    data/processed/ocr_report_v2.csv        (one row per file)
    data/processed/ocr_pages_v2.csv         (one row per page, for quarantine)
    data/processed/ocr_manifest_v2.csv      (sha256 of every .txt)

Run from the repository root:
    .venv/bin/python src/collect/ocr_columns.py --test 1991/F1991068.pdf:7
    .venv/bin/python src/collect/ocr_columns.py --force
"""

from __future__ import annotations

import argparse
import hashlib
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
import pytesseract
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/joradp"
REPORT = ROOT / "data/processed/pdf_report.csv"
OUT_ROOT = RAW / "text_v2"  # default, override with --out-root
OCR_REPORT = ROOT / "data/processed/ocr_report_v2.csv"
PAGES_REPORT = ROOT / "data/processed/ocr_pages_v2.csv"
MANIFEST = ROOT / "data/processed/ocr_manifest_v2.csv"

DPI = 300
MIN_FILE_CHARS = 1000
MIN_SKIP_BYTES = 2000
PSM = "--psm 3"
TESSERACT_LANG = {"ar": "ara", "fr": "fra"}


def render(doc: pymupdf.Document, index: int) -> Image.Image:
    pix = doc[index].get_pixmap(dpi=DPI, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def find_gutter(img: Image.Image) -> int | None:
    """x of the white vertical band separating two columns, or None."""
    gray = np.asarray(img.convert("L"))
    h, w = gray.shape
    body = gray[int(h * 0.20): int(h * 0.85)]  # skip full-width banners/titles
    ink = (body < 200).sum(axis=0).astype(float)  # dark pixels per pixel column

    k = 9  # median filter kills 1-2 px vertical rules
    padded = np.pad(ink, (k // 2, k // 2), mode="edge")
    smooth = np.array([np.median(padded[i:i + k]) for i in range(len(ink))])

    lo, hi = int(w * 0.35), int(w * 0.65)
    seg = smooth[lo:hi]
    valley = int(np.argmin(seg)) + lo
    base = float(np.median(smooth[int(w * 0.10): int(w * 0.90)]))
    if base <= 0 or seg.min() > 0.15 * base:
        return None
    return valley


def page_lines(img: Image.Image, tesseract_lang: str, rtl: bool = False) -> list[dict]:
    """Return text lines with their bounding boxes, in Tesseract's own order."""
    data = pytesseract.image_to_data(
        img, lang=tesseract_lang, config=PSM,
        output_type=pytesseract.Output.DICT,
    )
    grouped: dict[tuple[int, int, int], dict] = {}
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left, top = data["left"][i], data["top"][i]
        width, height = data["width"][i], data["height"][i]
        line = grouped.setdefault(
            key, {"words": [], "x0": left, "y0": top, "x1": left + width, "y1": top + height}
        )
        line["words"].append((left, word))
        line["x0"] = min(line["x0"], left)
        line["x1"] = max(line["x1"], left + width)
        line["y0"] = min(line["y0"], top)
        line["y1"] = max(line["y1"], top + height)

    lines = []
    for key, line in grouped.items():
        ordered_words = sorted(line["words"], key=lambda w: -w[0]) if rtl else sorted(line["words"])
        text = " ".join(word for _, word in ordered_words)
        lines.append(
            {
                "block": key[0],
                "x0": line["x0"], "x1": line["x1"],
                "y0": line["y0"], "y1": line["y1"],
                "cx": (line["x0"] + line["x1"]) / 2,
                "text": text,
            }
        )
    return lines


def reading_order(lines: list[dict], width: int, height: int, gutter: int | None,
                  rtl: bool = False) -> tuple[list[str], int]:
    """Order lines header -> left column -> right column -> footer. Returns (texts, n_cols)."""
    if not lines:
        return [], 1

    if gutter is None:
        ordered = sorted(lines, key=lambda l: (l["y0"], l["x0"]))
        return [l["text"] for l in ordered], 1

    margin = width * 0.08
    left, right, spanning = [], [], []
    for l in lines:
        if l["x0"] < gutter - margin and l["x1"] > gutter + margin:
            spanning.append(l)
        elif l["cx"] < gutter:
            left.append(l)
        else:
            right.append(l)

    two_columns = len(left) >= 2 and len(right) >= 2
    if not two_columns:
        ordered = sorted(lines, key=lambda l: (l["y0"], l["x0"]))
        return [l["text"] for l in ordered], 1

    header = sorted([l for l in spanning if l["y1"] < height * 0.5], key=lambda l: (l["y0"], l["x0"]))
    footer = sorted([l for l in spanning if l["y1"] >= height * 0.5], key=lambda l: (l["y0"], l["x0"]))
    columns = [right, left] if rtl else [left, right]
    ordered = header + [l for col in columns for l in sorted(col, key=lambda l: (l["y0"], l["x0"]))] + footer
    return [l["text"] for l in ordered], 2


def ocr_page(img: Image.Image, tesseract_lang: str) -> tuple[str, int, int]:
    """French: psm 3 + block reordering. Arabic: psm 4 per column.

    Measured on A1994020 p11: Arabic psm 3 returns ~226 words for ~270 visible,
    while psm 4 on the cropped halves returns 266 and keeps each column intact.
    """
    gutter = find_gutter(img)

    if tesseract_lang == "ara":
        if gutter is None:
            text = pytesseract.image_to_string(img, lang=tesseract_lang, config="--psm 4")
            return text, 1, len([l for l in text.splitlines() if l.strip()])
        pad = int(img.width * 0.01)
        right = pytesseract.image_to_string(
            img.crop((max(0, gutter - pad), 0, img.width, img.height)), lang=tesseract_lang, config="--psm 4")
        left = pytesseract.image_to_string(
            img.crop((0, 0, min(img.width, gutter + pad), img.height)), lang=tesseract_lang, config="--psm 4")
        text = right.strip() + "\n" + left.strip()
        return text, 2, len([l for l in text.splitlines() if l.strip()])

    lines = page_lines(img, tesseract_lang)
    texts, cols = reading_order(lines, img.width, img.height, gutter)
    return "\n".join(texts), cols, len(lines)


def out_path(out_root: Path, lang: str, year: int, file: str) -> Path:
    return out_root / lang / str(year) / (Path(file).stem + ".txt")


def ocr_file(lang_short: str, year: int, file: str, out_root: Path = OUT_ROOT, force: bool = False):
    tesseract_lang = TESSERACT_LANG[lang_short]
    src = RAW / "pdf" / lang_short / str(year) / file
    dst = out_path(out_root, lang_short, year, file)

    if not force and dst.exists() and dst.stat().st_size >= MIN_SKIP_BYTES:
        existing = dst.read_text(encoding="utf-8")
        return len(existing.split("\f")), len(existing.strip()), "skipped", 0.0, []

    if not src.exists():
        return 0, 0, "missing-source", 0.0, []

    started = time.time()
    pages: list[str] = []
    page_rows: list[dict] = []
    try:
        with pymupdf.open(src) as doc:
            for i in range(doc.page_count):
                try:
                    text, cols, n_lines = ocr_page(render(doc, i), tesseract_lang)
                except Exception as exc:
                    text, cols, n_lines = "", 0, 0
                    print(f"  WARN page {i + 1}: {type(exc).__name__}: {exc}")
                pages.append(text)
                page_rows.append(
                    {
                        "lang": lang_short, "year": year, "file": file, "page": i + 1,
                        "chars": len(text.strip()), "cols": cols, "lines": n_lines,
                    }
                )
    except Exception as exc:
        return 0, 0, f"failed: {type(exc).__name__}", time.time() - started, page_rows

    text = "\n\f\n".join(pages)
    chars = len(text.strip())
    if chars < MIN_FILE_CHARS:
        return len(pages), chars, "empty-or-short", time.time() - started, page_rows

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, dst)
    return len(pages), chars, "ok", time.time() - started, page_rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-OCR even if the .txt exists")
    parser.add_argument("--lang", choices=["fr", "ar"], help="only this language")
    parser.add_argument("--test", help="single page, e.g. 1991/F1991068.pdf:7 (1-based)")
    parser.add_argument("--out-root", help="output directory (default: data/raw/joradp/text_v2)")
    args = parser.parse_args()
    out_root = ROOT / args.out_root if args.out_root else OUT_ROOT

    if args.test:
        year_file, page_no = args.test.split(":")
        year, file = year_file.split("/")
        lang_dir = next((l for l in ("fr", "ar") if (RAW / "pdf" / l / year / file).exists()), None)
        if lang_dir is None:
            print(f"not found: {args.test}")
            return 1
        with pymupdf.open(RAW / "pdf" / lang_dir / year / file) as doc:
            text, cols, n_lines = ocr_page(render(doc, int(page_no) - 1), TESSERACT_LANG[lang_dir])
        print(f"[{lang_dir} {year}/{file} p{page_no}] cols={cols} lines={n_lines} chars={len(text)}")
        print(text)
        return 0

    if not REPORT.exists():
        print(f"missing report: {REPORT} — run inspect_pdfs.py first")
        return 1

    scans = pd.read_csv(REPORT)
    scans = scans[scans.kind == "scan"]
    if args.lang:
        scans = scans[scans.lang == args.lang]
    if scans.empty:
        print("no scanned file to process")
        return 0

    rows, page_rows_all = [], []
    counts: dict[str, int] = {}
    started = time.time()

    for row in scans.itertuples():
        label = f"{row.lang} {row.year}/{Path(row.file).stem}"
        try:
            pages, chars, status, seconds, page_rows = ocr_file(
                row.lang, row.year, row.file, out_root=out_root, force=args.force
            )
        except Exception as exc:
            pages, chars, status, seconds, page_rows = 0, 0, f"failed: {type(exc).__name__}", 0.0, []
        counts[status] = counts.get(status, 0) + 1
        rows.append(
            {"lang": row.lang, "year": row.year, "file": row.file,
             "pages": pages, "chars": chars, "status": status, "seconds": round(seconds, 1)}
        )
        page_rows_all.extend(page_rows)
        print(f"{status:16} {label:22} {pages:>3} pages {chars:>8} chars {seconds:>6.1f}s")

    def upsert(path: Path, new: pd.DataFrame, keys: list[str]) -> None:
        if new.empty:
            return
        if path.exists():
            old = pd.read_csv(path)
            old = old[~old.set_index(keys).index.isin(new.set_index(keys).index)]
            new = pd.concat([old, new], ignore_index=True)
        new.sort_values(keys).to_csv(path, index=False)

    upsert(OCR_REPORT, pd.DataFrame(rows), ["lang", "year", "file"])
    upsert(PAGES_REPORT, pd.DataFrame(page_rows_all), ["lang", "year", "file", "page"])

    manifest = []
    for txt in sorted(out_root.rglob("*.txt")):
        manifest.append(
            {"path": str(txt.relative_to(ROOT)), "bytes": txt.stat().st_size, "sha256": sha256(txt)}
        )
    pd.DataFrame(manifest).to_csv(MANIFEST, index=False)

    print(f"\n{counts}")
    print(f"total {(time.time() - started) / 60:.1f} min")
    print(f"reports: {OCR_REPORT.relative_to(ROOT)}, {PAGES_REPORT.relative_to(ROOT)}, {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
