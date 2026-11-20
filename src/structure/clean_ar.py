"""Clean the Arabic OCR output (layout only, never letters, never numbers).

Rules, learned from an audit of the 5 files (see doc 021 §1):
  * banner/header lines are dropped only in the FIRST 3 non-empty lines of a
    page (the Arabic running header is often glued with other junk, and a body
    line can legitimately start with "الموافق 11 يناير سنة 1997");
  * table-of-contents lines (dot leaders) and cover vocabulary are dropped
    everywhere;
  * Arabic-Indic digits are converted to ASCII (safe, reversible), invisible
    bidi marks removed;
  * digit-only lines are kept (a bare year is content, not a page number);
  * words are NOT joined across lines: Arabic is broken by spaces, not hyphens,
    so joining would invent words.

Usage:
    python src/structure/clean_ar.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

PAGE_SEP = "\n\f\n"

HEADER = re.compile(r"الجريدة الرسمي[ةّ]|الجريدة الرسمر|الجريدة الرس:")
BODY_WORDS = re.compile(r"المادة|ينشر|نشر هذا|نشر في|في الجريدة الرسمية")
ISSUE_BANNER = re.compile(r"^\s*العدد\b")
YEAR_BANNER = re.compile(r"^\s*السنة\s+(?:ال(?:أولى|اولى|ثانية|ثالثة|رابعة|خامسة|سادسة|سابعة|ثامنة|تاسعة|عاشرة|حادية|عشرون|ثلاثون|عشرين|ثلاثين))")
DATE_BANNER = re.compile(r"^\s*الموافق\b")
TOC = re.compile(r"\.{4,}|…{2,}")
COVER = re.compile(
    r"^\s*(?:الادارة والتحرير|الأمانة العامة للحكومة|الطبع والاشتراكات|المطبعة الرسمية|الهاتف|بلدان خارج دول|النسخة الاصلية)\b"
)
ORPHAN = re.compile(r"^[^\w\u0600-\u06FF]*$")
DIGITS_ONLY = re.compile(r"^[\d\s.,\-/]+$")

ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
EXTENDED_INDIC = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
INVISIBLE = re.compile("[\u200b-\u200f\u061c\u202a-\u202e\ufeff]")


def normalize(text: str) -> tuple[str, int]:
    text, n = INVISIBLE.subn("", text)
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(ARABIC_INDIC).translate(EXTENDED_INDIC)
    return text, n


def clean_ar(text: str) -> tuple[str, dict[str, int]]:
    counters = {
        "header_dropped": 0,
        "banner_dropped": 0,
        "toc_dropped": 0,
        "cover_dropped": 0,
        "orphan_dropped": 0,
        "digit_lines_kept": 0,
        "invisible_removed": 0,
    }
    text, counters["invisible_removed"] = normalize(text)
    before = len(text)

    out_pages = []
    for page in text.split(PAGE_SEP):
        kept, position = [], 0
        for line in page.splitlines():
            stripped = " ".join(line.split())
            if not stripped:
                kept.append("")
                continue
            position += 1
            if TOC.search(stripped):
                counters["toc_dropped"] += 1
                continue
            if COVER.match(stripped):
                counters["cover_dropped"] += 1
                continue
            looks_like_header = (
                HEADER.search(stripped)
                and not BODY_WORDS.search(stripped)
                and len(stripped) <= 120
            )
            if position <= 3 and (looks_like_header or ISSUE_BANNER.match(stripped)
                                  or YEAR_BANNER.match(stripped) or DATE_BANNER.match(stripped)):
                counters["header_dropped" if HEADER.search(stripped) else "banner_dropped"] += 1
                continue
            if ORPHAN.match(stripped) and not DIGITS_ONLY.match(stripped):
                counters["orphan_dropped"] += 1
                continue
            if DIGITS_ONLY.match(stripped):
                counters["digit_lines_kept"] += 1
            kept.append(stripped)
        page_text = "\n".join(kept)
        page_text = re.sub(r"\n{3,}", "\n\n", page_text).strip("\n")
        out_pages.append(page_text)

    cleaned = PAGE_SEP.join(p for p in out_pages if p)
    counters["pages_kept"] = sum(1 for p in out_pages if p)
    counters["chars_before"] = before
    counters["chars_after"] = len(cleaned)
    return cleaned, counters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/raw/joradp/text_v2/ar")
    ap.add_argument("--out", default="data/processed/text_clean/ar")
    ap.add_argument("--report", default="data/processed/clean_report_ar.csv")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    files = sorted(src.glob("*/*.txt"))
    if not files:
        print(f"no .txt under {src}")
        return 1

    rows = []
    for f in files:
        cleaned, c = clean_ar(f.read_text(encoding="utf-8"))
        target = out / f.parent.name / f.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(cleaned, encoding="utf-8")
        rows.append({"file": f.name, **c})
        ratio = c["chars_after"] / max(1, c["chars_before"])
        print(
            f"{f.name}: {c['pages_kept']} pages, {c['chars_before']} -> {c['chars_after']} "
            f"({ratio:.3f}) | têtes {c['header_dropped']}, bandeaux {c['banner_dropped']}, "
            f"sommaire {c['toc_dropped']}, couverture {c['cover_dropped']}, "
            f"ponctuation {c['orphan_dropped']}, lignes chiffres gardées {c['digit_lines_kept']}"
        )

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n-> {out} ({len(rows)} fichiers)\n-> {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
