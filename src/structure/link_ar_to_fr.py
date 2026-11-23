"""Link Arabic extracted texts to French IDs by gazette position.

Arabic OCR frequently reverses or damages law numbers. The French
extraction gets numbers right. This script matches Arabic texts to
their French counterparts using:
  1. Same gazette issue (year + issue number)
  2. Same text type (loi, decret, ordonnance, …)
  3. Order of appearance (page_start)

When a match is found the Arabic file is renamed to the French ID,
the reversed number in the heading is replaced with the correct one,
and index_ar.csv is updated with link_fr / link_method.

Usage:
    python src/structure/link_ar_to_fr.py
    python src/structure/link_ar_to_fr.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FR_INDEX = ROOT / "data" / "processed" / "texts" / "index.csv"
AR_INDEX = ROOT / "data" / "processed" / "texts_ar" / "index_ar.csv"
AR_DIR = ROOT / "data" / "processed" / "texts_ar"


def extract_num(texte_id: str) -> str | None:
    """Extract the law number part from an ID like 'loi-22-16' -> '22-16'."""
    m = re.match(r"[a-z]+-(\d+-\d+)$", texte_id)
    return m.group(1) if m else None


def fix_heading_number(content: str, old_num: str, new_num: str) -> str:
    """Replace the reversed number in the first few lines of the Arabic text."""
    old_a, old_b = old_num.split("-")
    new_a, new_b = new_num.split("-")
    lines = content.split("\n")
    fixed = []
    replacements = 0
    for i, line in enumerate(lines):
        if i < 5 and replacements < 2:
            new_line = re.sub(
                rf"\b{re.escape(old_a)}\s*[-–—]\s*{re.escape(old_b)}\b",
                f"{new_a}-{new_b}",
                line,
            )
            if new_line != line:
                replacements += 1
            fixed.append(new_line)
        else:
            fixed.append(line)
    return "\n".join(fixed)


def parse_issue(fname: str) -> tuple[str, int] | None:
    m = re.match(r"[FA](\d{4})(\d{3})\.txt", fname)
    if m:
        return (m.group(1), int(m.group(2)))
    m = re.match(r"jo-(\d{4})-(\d+)\.txt", fname)
    if m:
        return (m.group(1), int(m.group(2)))
    return None


def load_index(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be renamed without changing files")
    args = ap.parse_args()

    if not FR_INDEX.exists() or not AR_INDEX.exists():
        print(f"Missing index: {FR_INDEX} or {AR_INDEX}")
        return 1

    fr_rows = load_index(FR_INDEX)
    ar_rows = load_index(AR_INDEX)

    fr_by_issue: dict[tuple, list[dict]] = defaultdict(list)
    for r in fr_rows:
        issue = parse_issue(r["source_file"])
        if issue:
            fr_by_issue[issue].append(r)

    ar_by_issue: dict[tuple, list[dict]] = defaultdict(list)
    for r in ar_rows:
        issue = parse_issue(r["source_file"])
        if issue:
            ar_by_issue[issue].append(r)

    linked = 0
    skipped = 0
    already_correct = 0

    for issue in sorted(set(fr_by_issue) & set(ar_by_issue)):
        fr_texts = fr_by_issue[issue]
        ar_texts = ar_by_issue[issue]

        fr_by_type: dict[str, list[dict]] = defaultdict(list)
        for r in fr_texts:
            fr_by_type[r["type"]].append(r)
        for v in fr_by_type.values():
            v.sort(key=lambda r: int(r.get("page_start", 0)))

        ar_by_type: dict[str, list[dict]] = defaultdict(list)
        for r in ar_texts:
            ar_by_type[r["type"]].append(r)
        for v in ar_by_type.values():
            v.sort(key=lambda r: int(r.get("page_start", 0)))

        for text_type in set(fr_by_type) & set(ar_by_type):
            fr_list = fr_by_type[text_type]
            ar_list = ar_by_type[text_type]

            if len(fr_list) != len(ar_list):
                print(f"  SKIP issue {issue} type {text_type}: "
                      f"count mismatch FR={len(fr_list)} AR={len(ar_list)}")
                skipped += len(ar_list)
                continue

            for fr_r, ar_r in zip(fr_list, ar_list):
                fr_id = fr_r["texte_id"]
                ar_id = ar_r["texte_id"]

                if ar_id == fr_id:
                    ar_r["link_fr"] = fr_id
                    ar_r["link_method"] = "exact_match"
                    already_correct += 1
                    continue

                ar_path = Path(ar_r["path"])
                new_path = ar_path.parent / f"{fr_id}.txt"

                print(f"  {'[DRY] ' if args.dry_run else ''}"
                      f"{ar_id} -> {fr_id}  "
                      f"(issue {issue[0]}-{issue[1]:03d}, {text_type})")

                if not args.dry_run:
                    if ar_path.exists():
                        old_num = extract_num(ar_id)
                        new_num = extract_num(fr_id)
                        if old_num and new_num and old_num != new_num:
                            text = ar_path.read_text(encoding="utf-8")
                            text = fix_heading_number(text, old_num, new_num)
                            ar_path.write_text(text, encoding="utf-8")
                            print(f"    fixed heading: {old_num} -> {new_num}")
                        shutil.move(str(ar_path), str(new_path))
                    ar_r["texte_id"] = fr_id
                    ar_r["path"] = str(new_path)

                ar_r["link_fr"] = fr_id
                ar_r["link_method"] = "position_match"
                linked += 1

    if not args.dry_run:
        fields = list(ar_rows[0].keys())
        with AR_INDEX.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(ar_rows)

    print(f"\nLinked: {linked} | Already correct: {already_correct} | "
          f"Skipped (count mismatch): {skipped}")
    if args.dry_run:
        print("(dry run — no files changed)")
    else:
        print(f"-> {AR_INDEX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
