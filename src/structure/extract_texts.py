"""Cut a cleaned Journal Officiel issue into individual legal texts.

A text starts on a line whose *type* is at line start (references inside a
sentence are preceded by "la loi", "vu la loi", ... so they don't match). Two
forms exist:

    Loi n° 91-29 du 21 décembre 1991 ...        -> id "loi-91-29"
    Décret exécutif du 20 Rajab 1417 ...        -> unnumbered (nominations),
                                                   id "decret-1991-p2-3"

Plural headings ("Décrets exécutifs du ...") are treated like unnumbered
headings (they get an id of the form "decret-<year>-pNN-k").

What happens to each chunk (every chunk is written to the report):

    short (< --min-chars)                  -> dropped, reason "short"
    unknown type word                      -> dropped, reason "unknown_type"
    contains "Art." / "Article 1er"        -> kept,    reason "article"
    nomination wording, no article         -> kept,    reason "nomination_no_article"
    preamble wording ("Vu ...", "Le Président ...", "Par arrêté ..."), no article
                                           -> kept,    reason "body_no_article"
    anything else                          -> dropped, reason "toc"

When a numbered text appears twice, the longest occurrence wins (the summary
lists it before the real body).

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

# OCR junk that may sit in front of a heading. "!", "?", "{" and "}" were added
# (a Délibération heading appeared as "! Délibération du 18 Chaâbane 1417").
PREFIX = r"[|:—–>*·.!?{}]{0,3}"

BOUNDARY = re.compile(
    rf"^\s*{PREFIX}\s*(?P<type>{TYPE_WORD}|{PLURAL_WORD}){QUALIFIER}"
    # between the type word and "n°" / "du": spaces, or a stray colon
    # ("Ordonnance :n° 97-02")
    rf"(?:\s+|\s*:\s*)"
    rf"(?:n[°o]\s*(?P<num>\d{{1,3}}-\d{{1,3}})"
    rf"|du\s+(?P<day>\d{{1,2}})(?:er|[°*“”\"'’.])?\s+(?P<month>[A-Za-zéèûôàâç]+)\s+(?P<year>\d{{3,4}}))",
    re.M,
)

# Heading whose number and type word were read in the wrong order by the OCR:
#     97-01 du 2 Ramadhan 1417
#     Ordonnance n°
#     janvier 1997 ...
SPLIT_HEAD = re.compile(
    rf"^[ \t]*(?P<num>\d{{2,3}}-\d{{1,3}})[ \t]+(?P<rest>du[ \t]+\d{{1,2}}(?:er)?[ \t]+[A-Za-zéèûôàâç]+[ \t]+\d{{3,4}})[ \t]*\n"
    rf"[ \t]*(?P<type>{TYPE_WORD}){QUALIFIER}[ \t]+n[°o][ \t]*$",
    re.M,
)

# Two headings printed side by side on the same line ("... 91-509 du ... { Décret ... 91-510 ...").
# The two bodies are then interleaved too, so the chunk cannot be split safely:
# we only flag it.
MERGED_HEADING = re.compile(
    rf"(?<=\w)\s+[{{|]\s*{TYPE_WORD}{QUALIFIER}\s+n[°o]\s*\d"
)

ART = re.compile(r"(?m)^\s*(?:Art\.|Article\s+(?:\d|l[er]\b))")
PROMULGATION = re.compile(r"Promulgue la loi|Apr[èe]s adoption")

# A nomination / end-of-functions decree has no "Art." but its body says what
# happened to whom. The table of contents only has the title ("mettant fin",
# "portant nomination"), never these past/passive forms.
NOMINATION = re.compile(
    r"(?i)\b(?:il\s+est\s+(?:mis\s+fin|nomm[ée]e?)|sont\s+nomm[ée]s|est\s+nomm[ée]e?"
    r"|mis\s+fin\s+aux\s+fonctions|exerc[ée]es?\s+par)\b"
)
# Opening words of a real body (preamble, individual decision). A table of
# contents entry never starts a line with these.
BODY_MARKER = re.compile(
    r"(?mi)^\s*(?:Le\s+Pr[ée]sident\b|Vu\b|Apr[èe]s\s+adoption|Promulgue\b|D[ée]cr[èe]te\b"
    r"|Arr[êe]te\s*:|Par\s+(?:d[ée]cret|arr[êe]t[ée]|d[ée]cision)\b)"
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
PLURALS = {"lois", "ordonnances", "decrets", "décrets", "arrêtés", "arretes", "décisions", "decisions"}


@dataclass
class Found:
    kind: str
    num: str | None
    title: str
    body: str
    page: int
    numbered: bool = field(default=True)
    short: bool = field(default=False)


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


def all_marks(text: str) -> list[re.Match]:
    """Every heading found in the issue, in reading order."""
    split = list(SPLIT_HEAD.finditer(text))
    spans = [(m.start(), m.end()) for m in split]
    plain = [m for m in BOUNDARY.finditer(text) if not any(a <= m.start() < b for a, b in spans)]
    return sorted(split + plain, key=lambda m: m.start())


def find_texts(text: str, min_chars: int) -> list[Found]:
    """Cut the issue at every heading. Nothing is skipped here: short chunks and
    unknown types are returned too, so that main() can log them."""
    marks = all_marks(text)
    out: list[Found] = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        chunk = text[m.start() : end]
        raw_type = m.group("type").lower()
        kind = TYPES.get(raw_type)
        body = chunk.strip()
        body = re.sub(r"[,;]?\s*p\.\s*\d+\.?\s*$", "", body).strip()
        lines = [ln.strip() for ln in body.splitlines()]
        title = clean_title(lines)
        if m.re is SPLIT_HEAD:  # rebuild the title the OCR scrambled
            title = f"{m.group('type')} n° {m.group('num')} {m.group('rest')}"
        out.append(
            Found(
                kind=kind or "unknown",
                num=m.group("num"),
                title=title,
                body=body,
                page=page_of(text, m.start()),
                numbered=raw_type not in PLURALS and bool(m.group("num")),
                short=len(body) < min_chars,
            )
        )
    return out


def classify(it: Found) -> tuple[bool, str]:
    """Decide what to do with a chunk. Returns (keep, reason)."""
    if it.kind == "unknown":
        return False, "unknown_type"
    if it.short:
        return False, "short"
    if ART.search(it.body):
        return True, "article"
    if NOMINATION.search(it.body):
        return True, "nomination_no_article"
    if BODY_MARKER.search(it.body):
        return True, "body_no_article"
    return False, "toc"


def contamination(it: Found) -> list[str]:
    reasons = []
    if PROMULGATION.search(it.body) and not it.numbered:
        reasons.append("promulgation")
    if MERGED_HEADING.search(" ".join(it.body.splitlines()[:2])):
        reasons.append("merged_heading")
    return reasons


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
    stats = {"unnumbered": 0, "replaced": 0, "duplicate": 0}
    reasons: dict[str, int] = {}

    def log(f: Path, tid: str, status: str, reason: str, it: Found) -> None:
        reasons[reason] = reasons.get(reason, 0) + 1
        report.append(
            {
                "issue": f.name,
                "texte_id": tid,
                "status": status,
                "reason": reason,
                "page": it.page,
                "chars": len(it.body),
                "title": it.title[:120],
                "excerpt": re.sub(r"\s+", " ", it.body)[:80],
            }
        )

    for f in files:
        text = f.read_text(encoding="utf-8")
        issue_year = f.parent.name if f.parent.name.isdigit() else f.stem[1:5]
        found = find_texts(text, args.min_chars)
        seq: dict[int, int] = {}
        kept = 0

        for it in found:
            keep, reason = classify(it)
            if not keep:
                log(f, "", "dropped", reason, it)
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
                    log(f, tid, "replaced_longer", reason, it)
                else:
                    stats["duplicate"] += 1
                    log(f, tid, "duplicate", reason, it)
                continue

            target = out / issue_year / f"{tid}.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(it.body, encoding="utf-8")
            contam = contamination(it)
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
                "contaminated": int(bool(contam)),
                "contam_reason": "+".join(contam),
                "keep_reason": reason,
                "path": str(target),
            }
            log(f, tid, "kept", reason, it)
            kept += 1

        print(f"{f.name}: {len(found)} chunks, {kept} retenus")

    out.mkdir(parents=True, exist_ok=True)
    with (out / "index.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(next(iter(index.values())).keys()))
        w.writeheader()
        w.writerows(index.values())
    with Path(args.report).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["issue", "texte_id", "status", "reason", "page", "chars", "title", "excerpt"]
        )
        w.writeheader()
        w.writerows(report)

    numbered = sum(1 for r in index.values() if r["numbered"])
    print(
        f"\nمجموع: {len(index)} نصًّا ({numbered} مرقَّم، {len(index) - numbered} غير مرقَّم) | "
        f"مكرَّر {stats['duplicate']} | استُبدل بأطول {stats['replaced']}"
    )
    print("الأسباب: " + " | ".join(f"{k}={v}" for k, v in sorted(reasons.items())))
    for tid, it in sorted(index.items(), key=lambda kv: -kv[1]["chars"])[:5]:
        print(f"  {tid}: {it['chars']} حرفًا | {it['title'][:80]}")
    print(f"-> {out}/index.csv\n-> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())