"""Cut a cleaned Arabic Journal Officiel issue into individual legal texts.

Boundaries follow the printed form:
    أمر رقم 97-03 مؤرخ في ...        -> numbered
    مرسوم تنفيذي مؤرخ في 20 رجب ...  -> unnumbered (nominations)
A chunk without "المادة" is a table of contents / announcement and is dropped.

Arabic numbers in headings are unreliable: the OCR prints "7 9- 02" or reverses
them ("01-97"). We keep the raw string, flag `num_ok`, and only build a clean id
when the year part matches the issue year (printed or reversed).

Output:
    data/processed/texts_ar/<issue_year>/<texte_id>.txt
    data/processed/texts_ar/index_ar.csv
    data/processed/extract_report_ar.csv

Usage:
    python src/structure/extract_texts_ar.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TYPE_WORD = r"(?:أمر|قانون|مرسوم|قرار|مقرر|منشور|نظام|ملحق)"
QUALIFIER = r"(?:تنفيذي|رئاسي|وزاري|مشترك|داخلي|تكميلي|تشريعي|عضوي)"

DIACRITICS = r"[\u064B-\u0652\u0640]{0,3}"          # harakat / tatweel
BOUNDARY = re.compile(
    rf"^\s*[|:—–>*·.،؛\s]{{0,3}}(?P<type>{TYPE_WORD}){DIACRITICS}"
    rf"(?:\s+{QUALIFIER}{DIACRITICS})?\s+"
    rf"(?:رقم\s*(?P<num>\d{{1,3}}(?:[\s.]+\d{{1,2}})?(?:[\s.]*[-–—+][\s.]*\d{{1,3}})?)"
    rf"|م[ؤو]{{1,2}}{DIACRITICS}ر{DIACRITICS}خ{DIACRITICS}\s*[:：]?\s*(?:في\s+)?"
    rf"(?P<day>\d{{1,2}})\s+(?P<month>[^\s]+)(?:\s+عام\s+(?P<year>\d{{3,4}}))?)",
    re.M,
)
LOOSE = re.compile(
    rf"^\s*[|:—–>*·.،؛\s]{{0,6}}(?P<type>{TYPE_WORD}){DIACRITICS}[^\n]{{0,30}}?"
    rf"(?:رقم\s*\d|\d{{1,3}}\s*[-–—]\s*\d{{1,3}}|م[ؤو][^\n]{{0,4}}?خ)",
    re.M,
)
ARTICLE = re.compile(r"الماد[ةه]")
TRAILING_JUNK = re.compile(r"[\.\s،؛:—–\-|]{3,}$")

TYPES = {
    "أمر": "ordonnance",
    "قانون": "loi",
    "مرسوم": "decret",
    "قرار": "arrete",
    "مقرر": "decision",
    "منشور": "avis",
    "نظام": "reglement",
    "ملحق": "annexe",
}


@dataclass
class Found:
    kind: str
    num_raw: str | None
    num_ok: bool
    num_clean: str | None
    title: str
    body: str
    page: int
    numbered: bool


def page_of(text: str, offset: int) -> int:
    return text.count("\f", 0, offset) + 1


def parse_number(raw: str | None, issue_year: str) -> tuple[bool, str | None]:
    """Return (num_ok, clean 'YY-N') from a possibly damaged heading number."""
    if not raw:
        return False, None
    parts = re.findall(r"\d+", raw)
    yy = issue_year[-2:]
    if len(parts) == 3:
        a, b, nn = parts
        if (a + b)[::-1] != yy and (b + a) != yy:
            return False, None
    elif len(parts) == 2:
        a, b = parts
        if a.zfill(2) == yy:
            nn = b
        elif b.zfill(2) == yy:
            nn = a
        else:
            return False, None
    else:
        return False, None
    if not nn.isdigit() or len(nn) > 3:
        return False, None
    return True, f"{yy}-{int(nn):02d}"


def clean_title(lines: list[str]) -> str:
    title = " ".join(lines[:4])
    title = " ".join(title.split())
    title = re.sub(r"(?<=.)\s*\|.*", "", title)
    title = re.sub(r"^\s*\|\s*", "", title)
    title = re.sub(r"\s*[{}]\s*", " ", title)
    return TRAILING_JUNK.sub("", title).strip()[:300]


def find_texts(text: str, issue_year: str, min_chars: int) -> list[Found]:
    marks: list[re.Match] = []
    for m in sorted(list(BOUNDARY.finditer(text)) + list(LOOSE.finditer(text)),
                    key=lambda x: x.start()):
        if marks and m.start() < marks[-1].end():
            if m.start() >= marks[-1].end() - 1 and len(m.group(0)) > len(marks[-1].group(0)):
                marks[-1] = m
            continue
        marks.append(m)
    out: list[Found] = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.start() : end].strip()
        body = TRAILING_JUNK.sub("", body).strip()
        if len(body) < min_chars:
            continue
        kind = TYPES[m.group("type")]
        raw = m.groupdict().get("num")
        ok, clean = parse_number(raw, issue_year)
        out.append(
            Found(
                kind=kind,
                num_raw=" ".join(raw.split()) if raw else None,
                num_ok=ok,
                num_clean=clean,
                title=clean_title([ln.strip() for ln in body.splitlines() if ln.strip()]),
                body=body,
                page=page_of(text, m.start()),
                numbered=raw is not None,
            )
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/processed/text_clean/ar")
    ap.add_argument("--out", default="data/processed/texts_ar")
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--report", default="data/processed/extract_report_ar.csv")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    files = sorted(src.glob("*/*.txt"))
    if not files:
        print(f"no .txt under {src}")
        return 1

    index: dict[str, dict] = {}
    report: list[dict] = []
    stats = {"toc": 0, "duplicate": 0, "replaced": 0, "num_bad": 0}

    for f in files:
        text = f.read_text(encoding="utf-8")
        issue_year = f.parent.name if f.parent.name.isdigit() else f.stem[1:5]
        found = find_texts(text, issue_year, args.min_chars)
        seq: dict[int, int] = {}
        kept = 0

        for it in found:
            if not ARTICLE.search(it.body):
                stats["toc"] += 1
                report.append({"issue": f.name, "texte_id": "", "status": "toc_dropped",
                               "page": it.page, "chars": len(it.body)})
                continue
            if it.numbered and it.num_ok:
                tid = f"{it.kind}-{it.num_clean}"
            else:
                if it.numbered and not it.num_ok:
                    stats["num_bad"] += 1
                seq[it.page] = seq.get(it.page, 0) + 1
                tid = f"{it.kind}-{issue_year}-p{it.page:02d}-{seq[it.page]}"

            record = {
                "issue_year": issue_year,
                "title": it.title,
                "source_file": f.name,
                "page_start": it.page,
                "chars": len(it.body),
                "num_raw": it.num_raw or "",
                "num_ok": int(it.num_ok),
                "numbered": int(it.numbered),
                "link_fr": "",
                "link_method": "",
            }

            if tid in index:
                if len(it.body) > index[tid]["chars"]:
                    stats["replaced"] += 1
                    Path(index[tid]["path"]).write_text(it.body, encoding="utf-8")
                    index[tid].update(record)
                    status = "replaced_longer"
                else:
                    stats["duplicate"] += 1
                    status = "duplicate"
                report.append({"issue": f.name, "texte_id": tid, "status": status,
                               "page": it.page, "chars": len(it.body)})
                continue

            target = out / issue_year / f"{tid}.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(it.body, encoding="utf-8")
            index[tid] = {
                "texte_id": tid,
                "type": it.kind,
                **record,
                "path": str(target),
            }
            report.append({"issue": f.name, "texte_id": tid, "status": "kept",
                           "page": it.page, "chars": len(it.body)})
            kept += 1

        print(f"{f.name}: {len(found)} chunks, {kept} retenus")

    out.mkdir(parents=True, exist_ok=True)
    fields = ["texte_id", "type", "num_raw", "num_ok", "numbered", "issue_year", "title",
              "source_file", "page_start", "chars", "link_fr", "link_method", "path"]
    with (out / "index_ar.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for tid, rec in index.items():
            w.writerow({"texte_id": tid, **rec})
    with Path(args.report).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["issue", "texte_id", "status", "page", "chars"])
        w.writeheader()
        w.writerows(report)

    numbered = sum(1 for r in index.values() if r["numbered"])
    ok = sum(1 for r in index.values() if r["num_ok"])
    print(f"\nمجموع: {len(index)} نصًّا ({numbered} مرقَّم، {len(index) - numbered} غير مرقَّم) | "
          f"أرقام مقروءة {ok} | فهرس مُستبعَد {stats['toc']} | مكرَّر {stats['duplicate']}")
    print(f"-> {out}/index_ar.csv\n-> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
