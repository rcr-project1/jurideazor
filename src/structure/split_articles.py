"""General article splitter for all French and Arabic legal texts.

Run from any working directory:
    python src/structure/split_articles.py

Loi 90-11 is taken from the validated specialized output produced by
split_loi_90_11.py. Other files are split with the general FR/AR patterns.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"
TEXTS_FR = DATA / "texts"
TEXTS_AR = DATA / "texts_ar"
SPECIALIZED_LOI = DATA / "articles.json"
OUT_JSON = DATA / "articles_all.json"
OUT_CSV = DATA / "split_report.csv"

# Match article headings only at the beginning of a line. This avoids
# treating references such as "l'article 33" inside a paragraph as headings.
ART_FR = re.compile(
    r"^[ \t]*(Art(?:icle)?\.?[ \t]*)"
    r"(1er|ler|\d+(?:-\d+)?)"
    r"(?:°|º)?"
    r"(?:[ \t]*(?:bis|ter|quater))?"
    r"[ \t]*[.:]?[ \t]*[-–—:][ \t]*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)

AR_NUMBER = (
    r"\d+(?:-\d+)?|[٠-٩]+(?:-[٠-٩]+)?|"
    r"الأولى|الاولى|الأول|الاول|الثانية|الثالثة|الرابعة|"
    r"الخامسة|السادسة|السابعة|الثامنة|التاسعة|العاشرة"
)
ART_AR = re.compile(
    rf"^[ \t]*[\"'”“»]*[ \t]*(?:المادة|مادة)[ \t]*"
    rf"({AR_NUMBER})[ \t]*(?:[:：؛،.\-–—])[ \t]*(.*)$",
    re.MULTILINE,
)

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
AR_ORDINALS = {
    "الأولى": "1", "الاولى": "1", "الأول": "1", "الاول": "1",
    "الثانية": "2", "الثالثة": "3", "الرابعة": "4",
    "الخامسة": "5", "السادسة": "6", "السابعة": "7",
    "الثامنة": "8", "التاسعة": "9", "العاشرة": "10",
}


def normalize_article_number(number: str, lang: str) -> str:
    number = number.strip()
    if lang == "fr" and number.lower() in {"1er", "ler"}:
        return "1"
    if lang == "ar":
        return AR_ORDINALS.get(number, number.translate(ARABIC_DIGITS))
    return number


def split_file(path: Path, lang: str) -> list[dict]:
    """Split one file; preserve full text when no article headings are found."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    pattern = ART_FR if lang == "fr" else ART_AR
    matches = list(pattern.finditer(text))

    if not matches:
        return [{"article": None, "content": text.strip()}]

    records: list[dict] = []
    preamble = text[: matches[0].start()].strip()
    if len(preamble) > 50:
        records.append({"article": "preambule", "content": preamble})

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        number_group = 2 if lang == "fr" else 1
        number = normalize_article_number(match.group(number_group), lang)
        content = text[match.start():end].strip()
        if content:
            records.append({"article": number, "content": content})
    return records


def parse_filename(path: Path) -> tuple[str, int | None]:
    name = path.stem
    text_type = name.split("-")[0]
    if path.parent.name.isdigit():
        year = int(path.parent.name)
    else:
        found = re.search(r"(?:19|20)\d{2}", name)
        year = int(found.group()) if found else None
    return text_type, year


def load_specialized_loi_90_11() -> list[dict]:
    """Load the specialist's checked Loi 90-11 articles, not the weak generic split."""
    if not SPECIALIZED_LOI.exists():
        raise FileNotFoundError(
            f"Missing {SPECIALIZED_LOI}. First run: "
            "python src/structure/split_loi_90_11.py"
        )
    data = json.loads(SPECIALIZED_LOI.read_text(encoding="utf-8"))
    loi = [row for row in data if row.get("texte_id") == "loi-90-11"]
    if not loi:
        raise ValueError("No texte_id='loi-90-11' records in data/processed/articles.json")

    numbers = {str(row.get("article", "")).strip() for row in loi}
    missing = [str(n) for n in range(1, 159) if str(n) not in numbers]
    if missing:
        raise ValueError(f"Loi 90-11 specialist output is missing articles: {missing}")

    result = []
    for row in loi:
        content = (row.get("contenu") or "").strip()
        if not content:
            raise ValueError(f"Empty content for Loi 90-11 article {row.get('article')}")
        result.append({"article": str(row["article"]), "content": content})
    return result


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    all_records: list[dict] = []
    report_rows: list[dict] = []

    for lang, folder in (("fr", TEXTS_FR), ("ar", TEXTS_AR)):
        if not folder.exists():
            print(f"WARNING: input folder not found: {folder}")
            continue

        for path in sorted(folder.rglob("*.txt")):
            text_type, year = parse_filename(path)
            if lang == "fr" and path.name.lower() == "loi-90-11.txt":
                pieces = load_specialized_loi_90_11()
                method = "specialized_validated"
            else:
                pieces = split_file(path, lang)
                method = "general_regex"

            relative = path.relative_to(DATA).as_posix()
            for piece in pieces:
                content = piece["content"]
                all_records.append({
                    "source_file": relative,
                    "lang": lang,
                    "year": year,
                    "text_type": text_type,
                    "article": piece["article"],
                    "content": content,
                    "char_count": len(content),
                })

            numbered = sum(p["article"] not in (None, "preambule") for p in pieces)
            report_rows.append({
                "source_file": relative,
                "lang": lang,
                "year": year,
                "type": text_type,
                "articles_found": numbered,
                "records_created": len(pieces),
                "total_chars": sum(len(p["content"]) for p in pieces),
                "method": method,
            })

    OUT_JSON.write_text(
        json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = [
            "source_file", "lang", "year", "type", "articles_found",
            "records_created", "total_chars", "method",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report_rows)

    fr_count = sum(r["lang"] == "fr" for r in all_records)
    ar_count = sum(r["lang"] == "ar" for r in all_records)
    numbered_count = sum(r["article"] not in (None, "preambule") for r in all_records)
    print("\n========== SPLITTING REPORT ==========")
    print(f"Input files processed: {len(report_rows)}")
    print(f"Total records created: {len(all_records)}")
    print(f"FR records: {fr_count}")
    print(f"AR records: {ar_count}")
    print(f"Numbered article records: {numbered_count}")
    print(f"Full texts without articles: {sum(r['article'] is None for r in all_records)}")
    print(f"Preambles: {sum(r['article'] == 'preambule' for r in all_records)}")
    print(f"Generated: {OUT_JSON.relative_to(ROOT)}")
    print(f"Generated: {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
