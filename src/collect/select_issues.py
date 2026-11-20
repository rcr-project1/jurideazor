"""Build the week-2 collection plan: data/processed/issues_selected.csv.

Input : data/raw/joradp/index/journal-officiel-archive.csv (UpGrowth index, CC BY 4.0)
Output: data/processed/issues_selected.csv

Selection = issues carrying amendments/related texts of Law 90-11:
            KNOWN (historical four) + FROM_CORPUS_PLAN (identified in PR #17)
            + optional data/corpus_index.csv if that file exists
            + a fixed evaluation sample (2 issues per year: 1993, 2005, 2010, 2020).

The evaluation sample is a commodity sample frozen on 2026-11-16, not a random
draw: changing it would invalidate the PDFs, OCR and texts already collected.

Run from the repository root:
    .venv/bin/python src/collect/select_issues.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
INDEX = REPO / "data/raw/joradp/index/journal-officiel-archive.csv"
CORPUS_INDEX = REPO / "data/corpus_index.csv"
OUT = REPO / "data/processed/issues_selected.csv"

KNOWN = {(1991, 68), (1994, 20), (1997, 3), (2015, 40)}
# From PR #17 (feat/corpus-plan, b26afee) until that PR is merged.
FROM_CORPUS_PLAN = {
    (1990, 17),  # original Law 90-11
    (1990, 6),  # Laws 90-03 and 90-04
    (1988, 4),  # Law 88-07
    (1996, 43),  # Ordinance 96-21
    (2017, 76),  # Law 17-11 (LFC 2018)
    (2022, 49),  # Law 22-16
}
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


def year_issue(url: object) -> tuple[int, int] | None:
    """Return (year, issue) from a JORADP URL, or None."""
    if not isinstance(url, str):
        return None
    text = url.strip()
    m = re.search(r"/[FA](\d{4})(\d{3})\.pdf", text, re.I)  # .../F1991068.pdf
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"/(\d{4})/(\d{3})/", text)  # .../Jo8499/1990/017/FP488.pdf
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"/(\d{4})/(\d{3})\.pdf", text, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else None


def pairs_from_corpus_index(path: Path) -> set[tuple[int, int]]:
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    pairs: set[tuple[int, int]] = set()
    for col in ("url_fr", "url_ar"):
        if col in df.columns:
            for url in df[col]:
                pair = year_issue(url)
                if pair:
                    pairs.add(pair)
    return pairs


def main() -> int:
    if not INDEX.exists():
        print(f"missing index: {INDEX}", file=sys.stderr)
        print(
            "download the UpGrowth journal index (CC BY 4.0) and place its CSV "
            "at data/raw/joradp/index/journal-officiel-archive.csv",
            file=sys.stderr,
        )
        return 1

    df = pd.read_csv(INDEX)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        print(f"unexpected columns, missing {missing}", file=sys.stderr)
        print(f"found: {df.columns.tolist()}", file=sys.stderr)
        return 1

    df = df.copy()
    df["issue"] = df["issue"].astype(int)
    plan = set(KNOWN) | set(FROM_CORPUS_PLAN) | pairs_from_corpus_index(CORPUS_INDEX)

    known_mask = df.apply(lambda r: (int(r.year), int(r.issue)) in plan, axis=1)
    sample = df[df.year.isin(SAMPLE_YEARS)].groupby("year").head(2)

    sel = (
        pd.concat([df[known_mask], sample])
        .drop_duplicates(["year", "issue"])
        .sort_values(["year", "issue"])
        .reset_index(drop=True)
    )

    def label(row) -> tuple[str, str]:
        pair = (int(row.year), int(row.issue))
        if pair in KNOWN:
            return "known", "amending text of Law 90-11"
        if pair in FROM_CORPUS_PLAN or pair in plan:
            return "corpus_plan", "text identified in PR #17"
        return "sample", "evaluation sample (fixed 2026-11-16)"

    labels = sel.apply(label, axis=1)
    sel["source"] = [x[0] for x in labels]
    sel["reason"] = [x[1] for x in labels]

    found = {(int(y), int(i)) for y, i in zip(sel.year, sel.issue)}
    absent = sorted(plan - found)
    if absent:
        print(f"WARNING: planned issues not in the index: {absent}", file=sys.stderr)

    cols = [
        "year",
        "issue",
        "edition_fr",
        "edition_ar",
        "url_fr",
        "url_ar",
        "year_fully_probed",
        "source",
        "reason",
    ]
    if "ug_ref" in sel.columns:
        cols.append("ug_ref")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sel[cols].to_csv(OUT, index=False)

    print(sel[["year", "issue", "edition_fr", "edition_ar", "source"]].to_string(index=False))
    expected = len(plan) + 2 * len(SAMPLE_YEARS)
    print(f"\nrows: {len(sel)} (upper bound {expected}: {len(plan)} planned + 8 sample)")
    print(f"wrote: {OUT.relative_to(REPO)}")
    print(
        "editions present: fr={} ar={}".format(
            int(sel.edition_fr.sum()), int(sel.edition_ar.sum())
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
