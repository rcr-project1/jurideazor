"""Sanity check of 4-digit numbers in the AR edition against the FR one.

What this can and cannot do (learned the hard way, 17/11):
  * CAN: flag AR numbers that exist nowhere in the FR edition of the same issue
    ("invented" numbers) and report how many digit runs the OCR split with
    spaces ("7 9- 02").
  * CANNOT: measure per-character digit accuracy, and CANNOT use raw year
    counts as a reference: each edition prints its own page header (FR repeats
    the Gregorian year, AR repeats the Hijri one), so counts are asymmetric.
    For accuracy use cer.py on an aligned span.

Usage:
    python src/eval/digit_check.py
    python src/eval/digit_check.py --root data/raw/joradp/text_v2 \
        --out data/processed/digit_check.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cer import normalize

YEAR_RE = re.compile(r"(?<![\d/.-])(1[89]\d{2}|2\d{3})(?![\d/.-])")
SPLIT_RE = re.compile(r"\d\s+\d")


def gregorian(text: str) -> Counter:
    return Counter(YEAR_RE.findall(text))


def context(text: str, value: str, width: int = 40) -> str:
    for m in YEAR_RE.finditer(text):
        if m.group(1) == value:
            snip = text[max(0, m.start() - width) : m.end() + width]
            return " ".join(snip.split())
    return ""


def issue_pairs(root: Path) -> list[tuple[Path, Path]]:
    out = []
    for fr in sorted((root / "fr").glob("*/*.txt")):
        ar = root / "ar" / fr.parent.name / ("A" + fr.name[1:])
        if ar.exists():
            out.append((fr, ar))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/raw/joradp/text_v2")
    ap.add_argument("--out", default="data/processed/digit_check.csv")
    ap.add_argument("--examples", type=int, default=4)
    args = ap.parse_args()

    root = Path(args.root)
    pairs = issue_pairs(root)
    if not pairs:
        print(f"no FR/AR pairs under {root}")
        return 1

    rows, total_ar, total_absent = [], 0, 0
    for fr_path, ar_path in pairs:
        fr = normalize(fr_path.read_text(encoding="utf-8"))
        ar = normalize(ar_path.read_text(encoding="utf-8"))
        fy, ay = gregorian(fr), gregorian(ar)
        absent = {v: n for v, n in ay.items() if v not in fy}
        total_ar += sum(ay.values())
        total_absent += sum(absent.values())
        top = sorted(absent.items(), key=lambda kv: -kv[1])[: args.examples]

        rows.append(
            {
                "issue": fr_path.name,
                "ar_gregorian": sum(ay.values()),
                "ar_absent_from_fr": sum(absent.values()),
                "ar_absent_pct": round(100 * sum(absent.values()) / max(1, sum(ay.values())), 1),
                "top_absent": " ".join(f"{v}x{n}" for v, n in top),
                "fr_gregorian": sum(fy.values()),
                "fr_absent_from_ar": sum((fy - ay).values()),
                "split_groups_fr": len(SPLIT_RE.findall(fr)),
                "split_groups_ar": len(SPLIT_RE.findall(ar)),
            }
        )

        print(f"\n=== {fr_path.name} ===")
        print(
            f"  أرقام 4 خانات عربية: {sum(ay.values())} | غائبة عن الفرنسية: "
            f"{sum(absent.values())} ({rows[-1]['ar_absent_pct']}%)"
        )
        for v, n in top:
            print(f"    {v} x{n}  …{context(ar, v)}…")
        print(
            f"  مجموعات أرقام مقطوعة بمسافة: FR {rows[-1]['split_groups_fr']} | "
            f"AR {rows[-1]['split_groups_ar']}"
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(
        f"\nالمجموع: {total_absent} رقمًا عربيًا غائبًا عن الفرنسية من {total_ar} "
        f"({100 * total_absent / max(1, total_ar):.1f}%)"
    )
    print(f"-> {out} ({len(rows)} صفوف)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
