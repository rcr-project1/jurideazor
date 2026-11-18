"""Cut a cleaned Journal Officiel issue into individual legal texts.

A text starts on a line whose *type* is at line start (references inside a
sentence are preceded by "la loi", "vu la loi", ... so they don't match). Two
forms exist:

    Loi n° 91-29 du 21 décembre 1991 ...        -> id "loi-91-29"
    Décret exécutif du 20 Rajab 1417 ...        -> unnumbered (nominations),
                                                   id "decret-1991-p2-3"

Plural headings ("Décrets exécutifs du ...") only close the previous text; they
are not extracted. Chunks without any "Art." line are tables of contents and are
dropped (counted as `toc_dropped`). When a numbered text appears twice, the
longest occurrence wins (the summary lists it before the real body).

Output:
    data/processed/texts/<issue_year>/<texte_id>.txt
    data/processed/texts/index.csv
    data/processed/extract_report.csv

Usage:
    python src/structure/extract_texts.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TYPE_WORD = r"(?:LOI|Loi|ORDONNANCE|Ordonnance|DECRET|Décret|ARRETE|Arrêté|DECISION|Décision|DELIBERATION|Délibération|AVIS|Avis)"
PLURAL_WORD = r"(?:LOIS|Lois|ORDONNANCES|Ordonnances|DECRETS|Décrets|ARRETES|Arrêtés|DECISIONS|Décisions|AVIS)"
QUALIFIER = r"(?:\s+(?:ex[ée]cutifs?|pr[ée]sidentiels?|minist[ée]riels?))?"

BOUNDARY = re.compile(
    rf"^\s*[|:—–>*·.]{{0,3}}\s*(?P<type>{TYPE_WORD}|{PLURAL_WORD}){QUALIFIER}\s+"
    rf"(?:n[°o]\s*(?P<num>\d{{1,3}}-\d{{1,3}})"
    rf"|du\s+(?P<day>\d{{1,2}})(?:er|[°*“”\"'’.])?\s+(?P<month>[A-Za-zéèûôàâç]+)\s+(?P<year>\d{{3,4}}))",
    re.M,
)
ART = re.compile(r"(?m)^\s*(?:Art\.|Article\s+(?:\d|l[er]\b))")
PROMULGATION = re.compile(r"Promulgue la loi|Apr[èe]s adoption")
SUBJECT = re.compile(
    r"^\s*(?:LOI|Loi|ORDONNANCE|Ordonnance|DECRET|Décret|ARRETE|Arrêté|DECISION|Décision|DELIBERATION|Délibération|AVIS|Avis)"
)

TYPES = {
    "loi": "loi",
    "ordonnance": "ordonnance",
    "decret": "decret",
    "décret": "decret",
    "arrêté": "arrete",
    "arrete": "arrete",
    "décision": "decision",
    "decision": "decision",
    "avis": "avis",
    "délibération": "deliberation",
    "deliberation": "deliberation",
    "lois": "loi",
    "ordonnances": "ordonnance",
    "decrets": "decret",
    "décrets": "decret",
    "arrêtés": "arrete",
    "arretes": "arrete",
    "décisions": "decision",
    "decisions": "decision",
}


@dataclass
class Found:
    kind: str
    num: str | None
    title: str
    body: str
    page: int
    numbered: bool = field(default=True)


def page_of(text: str, offset: int) -> int:
    return text.count("\f", 0, offset) + 1


def clean_title(lines: list[str]) -> str:
    title_lines = []
    for ln in lines[:4]:
        if not ln:
            continue
        title_lines.append(ln)
        if re.search(r"\b(?:du|de|en)\s+\d{1,2}(?:er)?\s+\w+\s+\d{4}\b", ln, re.I):
            break
        if ART.match(ln):
            break
    title = re.sub(r"\s+", " ", " ".join(title_lines)).strip()
    return re.sub(r"[,;]?\s*p\.\s*\d+\.?\s*$", "", title)[:300]


def find_texts(text: str, min_chars: int) -> list[Found]:
    marks = list(BOUNDARY.finditer(text))
    out: list[Found] = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        chunk = text[m.start() : end]
        raw_type = m.group("type").lower()
        kind = TYPES.get(raw_type)
        if kind is None:
            continue
        body = chunk.strip()
        body = re.sub(r"[,;]?\s*p\.\s*\d+\.?\s*$", "", body).strip()
        if len(body) < min_chars:
            continue
        lines = [ln.strip() for ln in body.splitlines()]
        out.append(
            Found(
                kind=kind,
                num=m.group("num"),
                title=clean_title(lines),
                body=body,
                page=page_of(text, m.start()),
                numbered=raw_type not in {"lois", "ordonnances", "decrets", "décrets", "arrêtés", "arretes", "décisions", "decisions"} and bool(m.group("num")),
            )
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/processed/text_clean/fr")
    ap.add_argument("--out", default="data/processed/texts")
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--report", default="data/processed/extract_report.csv")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    files = sorted(src.glob("*/*.txt")) or sorted(src.glob("*.txt"))
    if not files:
        print(f"no .txt under {src}")
        return 1

    index: dict[str, dict] = {}
    report: list[dict] = []
    stats = {"toc": 0, "unnumbered": 0, "replaced": 0, "duplicate": 0}

    for f in files:
        text = f.read_text(encoding="utf-8")
        issue_year = f.parent.name if f.parent.name.isdigit() else f.stem[1:5]
        found = find_texts(text, args.min_chars)
        seq: dict[int, int] = {}
        kept = 0

        for it in found:
            if not ART.search(it.body):
                stats["toc"] += 1
                report.append({"issue": f.name, "texte_id": "", "status": "toc_dropped", "page": it.page, "chars": len(it.body)})
                continue

            if it.numbered and it.num:
                tid = f"{it.kind}-{it.num}"
            else:
                stats["unnumbered"] += 1
                seq[it.page] = seq.get(it.page, 0) + 1
                tid = f"{it.kind}-{issue_year}-p{it.page:02d}-{seq[it.page]}"

            if tid in index:
                if it.numbered and len(it.body) > index[tid]["chars"]:
                    stats["replaced"] += 1
                    target = Path(index[tid]["path"])
                    target.write_text(it.body, encoding="utf-8")
                    index[tid].update(
                        {"title": it.title, "source_file": f.name, "page_start": it.page, "chars": len(it.body)}
                    )
                    status = "replaced_longer"
                else:
                    stats["duplicate"] += 1
                    status = "duplicate"
                report.append({"issue": f.name, "texte_id": tid, "status": status, "page": it.page, "chars": len(it.body)})
                continue

            target = out / issue_year / f"{tid}.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(it.body, encoding="utf-8")
            index[tid] = {
                "texte_id": tid,
                "type": it.kind,
                "num": it.num or "",
                "numbered": int(it.numbered),
                "issue_year": issue_year,
                "title": it.title,
                "source_file": f.name,
                "page_start": it.page,
                "chars": len(it.body),
                "contaminated": int(PROMULGATION.search(it.body) is not None and not it.numbered),
                "path": str(target),
            }
            report.append({"issue": f.name, "texte_id": tid, "status": "kept", "page": it.page, "chars": len(it.body)})
            kept += 1

        print(f"{f.name}: {len(found)} chunks, {kept} retenus")

    out.mkdir(parents=True, exist_ok=True)
    with (out / "index.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(next(iter(index.values())).keys()))
        w.writeheader()
        w.writerows(index.values())
    with Path(args.report).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["issue", "texte_id", "status", "page", "chars"])
        w.writeheader()
        w.writerows(report)

    numbered = sum(1 for r in index.values() if r["numbered"])
    print(
        f"\nمجموع: {len(index)} نصًّا ({numbered} مرقَّم، {len(index) - numbered} غير مرقَّم) | "
        f"فهرس مُستبعَد {stats['toc']} | مكرَّر {stats['duplicate']} | استُبدل بأطول {stats['replaced']}"
    )
    for tid, it in sorted(index.items(), key=lambda kv: -kv[1]["chars"])[:5]:
        print(f"  {tid}: {it['chars']} حرفًا | {it['title'][:80]}")
    print(f"-> {out}/index.csv\n-> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
