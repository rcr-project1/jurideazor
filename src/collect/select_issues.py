"""Build the week-2 collection plan: data/processed/issues_selected.csv.

Input : data/raw/joradp/index/journal-officiel-archive.csv (UpGrowth index, CC BY 4.0)
Output: data/processed/issues_selected.csv

Selection = known issues carrying amendments/related texts of Law 90-11
            + a small evaluation sample (2 issues per year: 1993, 2005, 2010, 2020).

Run from the repository root:
    .venv/bin/python src/collect/select_issues.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "data/raw/joradp/index/journal-officiel-archive.csv"
OUT = REPO / "data/processed/issues_selected.csv"

KNOWN = {(1991, 68), (1994, 20), (1997, 3), (2015, 40)}
SAMPLE_YEARS = (1993, 2005, 2010, 2020)
EXPECTED_COLUMNS = [
    "year",
    "issue",
    "edition_fr",
    "edition_ar",
    "url_fr",
    "url_ar",
    "year_fully_probed",
]


def main() -> int:
    if not INDEX.exists():
        print(f"missing index: {INDEX}", file=sys.stderr)
        print("run step 2 of project_one/005_خطوات_بدء_الجمع.md first", file=sys.stderr)
        return 1

    df = pd.read_csv(INDEX)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        print(f"unexpected columns, missing {missing}", file=sys.stderr)
        print(f"found: {df.columns.tolist()}", file=sys.stderr)
        return 1

    df = df.copy()
    df["issue"] = df["issue"].astype(int)

    known_mask = df.apply(lambda r: (int(r.year), int(r.issue)) in KNOWN, axis=1)
    sample = df[df.year.isin(SAMPLE_YEARS)].groupby("year").head(2)

    sel = (
        pd.concat([df[known_mask], sample])
        .drop_duplicates(["year", "issue"])
        .sort_values(["year", "issue"])
        .reset_index(drop=True)
    )
    sel["reason"] = [
        "amending text of Law 90-11" if k else "evaluation sample"
        for k in ((int(y), int(i)) in KNOWN for y, i in zip(sel.year, sel.issue))
    ]

    found = {(int(y), int(i)) for y, i in zip(sel.year, sel.issue)}
    absent = sorted(KNOWN - found)
    if absent:
        print(f"WARNING: known issues not in the index: {absent}", file=sys.stderr)

    cols = [
        "year",
        "issue",
        "edition_fr",
        "edition_ar",
        "url_fr",
        "url_ar",
        "year_fully_probed",
        "reason",
    ]
    if "ug_ref" in sel.columns:
        cols.append("ug_ref")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sel[cols].to_csv(OUT, index=False)

    print(sel[["year", "issue", "edition_fr", "edition_ar", "reason"]].to_string(index=False))
    print(f"\nrows: {len(sel)} (expected {len(KNOWN) + 2 * len(SAMPLE_YEARS)})")
    print(f"wrote: {OUT.relative_to(REPO)}")
    print(
        "editions present: fr={} ar={}".format(
            int(sel.edition_fr.sum()), int(sel.edition_ar.sum())
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
