"""Clean the French OCR output without touching numbers.

Design rule: this module may remove *layout*, never *content*. No digit, no
comma inside a number, no date is modified. Every removed line is counted so
the report can prove what was thrown away.

Usage:
    python src/structure/clean_text.py
    python src/structure/clean_text.py --in data/raw/joradp/text_v2/fr \
        --out data/processed/text_clean/fr \
        --report data/processed/clean_report.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

PAGE_SEP = "\n\f\n"

HEADER_PATTERNS = [
    re.compile(r"^journal\s+officiel", re.I),
    re.compile(r"^de\s+la\s+r[ée]publique\s+alg[ée]rienne", re.I),
    re.compile(r"^n[°o]\s*\d+\s*$", re.I),
    re.compile(r"^\d{1,2}\s*[èe]re?\s*ann[ée]e\s*$", re.I),
    re.compile(r"^correspondant\s+au\s+\d{1,2}(?:er)?\s+\w+\s+\d{4}\s*$", re.I),
    re.compile(r"^(direction\s+et\s+r[ée]daction|secr[ée]tariat\s+g[ée]n[ée]ral)\s*:?$", re.I),
    re.compile(r"^(abonnement|etranger|[ée]tranger|du\s+gouvernement|tarif\s+des\s+insertions)\s*:?$", re.I),
]
DIGIT_ONLY = re.compile(r"^[\d.,\s]+$")
COMPOUND_PREFIXES = {
    "sous", "contre", "anti", "auto", "co", "pre", "post", "non", "semi",
    "vice", "ex", "neo", "ultra", "supra", "inter", "intra", "multi", "mono",
    "bi", "tri", "hyper", "hypo", "macro", "micro", "mini", "tele", "demi",
    "mi", "quasi", "pro", "trans", "extra", "archi", "arriere", "avant",
}
LEADERS = re.compile(r"\.{5,}")
ORPHAN = re.compile(r"^[|:—–\-.,;·/\\_=+*~^<>()\[\]{}\s]*$")
HYPHEN_BREAK = re.compile(r"([^\W\d_]+)-[ \t]*\n(?=[^\W\d_])", re.UNICODE)
ART_COMMA = re.compile(r"\bArt,")


def normalize_chars(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return (
        text.replace("\u00ad", "")
        .replace("œ", "oe")
        .replace("Œ", "OE")
        .replace("æ", "ae")
        .replace("Æ", "AE")
    )


def clean_french(text: str) -> tuple[str, dict[str, int]]:
    counters = {
        "header_dropped": 0,
        "digit_lines_kept": 0,
        "hyphen_kept": 0,
        "leaders_dropped": 0,
        "orphan_dropped": 0,
        "hyphen_joined": 0,
        "art_commas_fixed": 0,
    }
    text = normalize_chars(text)
    counters["art_commas_fixed"] = len(ART_COMMA.findall(text))
    text = ART_COMMA.sub("Art.", text)
    def join_word(m: re.Match) -> str:
        left = m.group(1)
        key = unicodedata.normalize("NFD", left.lower())[:-1] if left.lower().endswith("e") else left.lower()
        key = "".join(c for c in unicodedata.normalize("NFD", left.lower()) if not unicodedata.combining(c))
        if key in COMPOUND_PREFIXES:
            counters["hyphen_kept"] += 1
            return left + "-"
        counters["hyphen_joined"] += 1
        return left

    text = HYPHEN_BREAK.sub(join_word, text)

    out_pages = []
    for page in text.split(PAGE_SEP):
        kept = []
        for line in page.splitlines():
            stripped = line.strip()
            if not stripped:
                kept.append("")
                continue
            if any(p.match(stripped) for p in HEADER_PATTERNS):
                counters["header_dropped"] += 1
                continue
            if DIGIT_ONLY.match(stripped):
                counters["digit_lines_kept"] += 1
                kept.append(stripped)
                continue
            if LEADERS.search(stripped):
                counters["leaders_dropped"] += 1
                continue
            if ORPHAN.match(stripped) and not re.search(r"\w", stripped):
                counters["orphan_dropped"] += 1
                continue
            kept.append(stripped)
        page_text = "\n".join(kept)
        page_text = re.sub(r"\n{3,}", "\n\n", page_text).strip("\n")
        out_pages.append(page_text)

    cleaned = PAGE_SEP.join(p for p in out_pages if p)
    counters["pages_kept"] = len([p for p in out_pages if p])
    counters["chars_before"] = len(text)
    counters["chars_after"] = len(cleaned)
    return cleaned, counters


def iter_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob("*/*.txt"))
    return [path]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/raw/joradp/text_v2/fr")
    ap.add_argument("--out", default="data/processed/text_clean/fr")
    ap.add_argument("--report", default="data/processed/clean_report.csv")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    files = iter_inputs(src)
    if not files:
        print(f"no .txt under {src}")
        return 1

    rows = []
    for f in files:
        cleaned, c = clean_french(f.read_text(encoding="utf-8"))
        target = out / f.parent.name / f.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(cleaned, encoding="utf-8")
        rows.append({"file": f.name, **c})
        ratio = c["chars_after"] / max(1, c["chars_before"])
        print(
            f"{f.name}: {c['pages_kept']} pages, {c['chars_before']} -> {c['chars_after']} "
            f"({ratio:.3f}) | en-têtes {c['header_dropped']}, n° page (gardés) {c['digit_lines_kept']}, "
            f"points de suite {c['leaders_dropped']}, lignes ponctuation {c['orphan_dropped']}, "
            f"césures jointes {c['hyphen_joined']} / gardées {c['hyphen_kept']}, "
            f"lignes chiffres gardées {c['digit_lines_kept']}, Art, {c['art_commas_fixed']}"
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
