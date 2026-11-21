"""Create retrieval-ready chunks from data/processed/articles_all.json.

Run from the project root:
    python src/structure/chunk_texts.py

Each numbered article remains one chunk. Text records without an article are
kept whole when <= 500 words; longer records are grouped by paragraphs.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "processed" / "articles_all.json"
OUT_DIR = ROOT / "data" / "processed"
CHUNKS_PATH = OUT_DIR / "chunks.json"
REPORT_PATH = OUT_DIR / "chunk_report.csv"
MAX_WORDS = 500


def slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")
    return value or "text"


def split_long_text(content: str, max_words: int = MAX_WORDS) -> list[str]:
    """Group paragraphs without dropping text; split oversized paragraphs by words."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content.strip()) if p.strip()]
    if not paragraphs:
        return [content.strip()] if content.strip() else []

    units: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if len(words) <= max_words:
            units.append(paragraph)
        else:
            # A single paragraph can exceed the target; split it safely by words.
            units.extend(" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words))

    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for unit in units:
        n = len(unit.split())
        if current and count + n > max_words:
            chunks.append("\n\n".join(current))
            current, count = [], 0
        current.append(unit)
        count += n
    if current:
        chunks.append("\n\n".join(current))
    return chunks



def make_chunks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for record in records:
        content = str(record.get("content") or "").strip()
        if not content:
            continue

        article = record.get("article")

        # Numbered articles remain intact.
        if article not in (None, "", "preambule"):
            pieces = [content]
        elif len(content.split()) <= MAX_WORDS:
            pieces = [content]
        else:
            pieces = split_long_text(content)

        source_stem = Path(
            str(record.get("source_file", "text"))
        ).stem

        lang = str(record.get("lang") or "xx").strip().lower()
        article_part = (
            slug(article) if article not in (None, "") else "full"
        )

        for index, piece in enumerate(pieces, start=1):
            suffix = f"_part_{index}" if len(pieces) > 1 else ""

            base_id = f"{lang}_{slug(source_stem)}_{article_part}{suffix}"
            chunk_id = base_id

            # Guarantee global uniqueness, even if an article number repeats.
            duplicate_index = 2
            while chunk_id in used_ids:
                chunk_id = f"{base_id}_dup_{duplicate_index}"
                duplicate_index += 1

            used_ids.add(chunk_id)

            chunks.append({
                "chunk_id": chunk_id,
                "source_file": record.get("source_file"),
                "lang": record.get("lang"),
                "year": record.get("year"),
                "text_type": record.get("text_type"),
                "article": article if article not in ("",) else None,
                "content": piece,
                "char_count": len(piece),
            })

    return chunks


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Fichier introuvable: {INPUT}. Lance d'abord split_articles.py."
        )
    records = json.loads(INPUT.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("articles_all.json doit contenir une liste JSON.")

    chunks = make_chunks(records)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    with REPORT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "chunk_id", "source_file", "lang", "year", "text_type",
            "article", "word_count", "char_count"
        ])
        writer.writeheader()
        for c in chunks:
            writer.writerow({
                "chunk_id": c["chunk_id"], "source_file": c["source_file"],
                "lang": c["lang"], "year": c["year"], "text_type": c["text_type"],
                "article": c["article"], "word_count": len(c["content"].split()),
                "char_count": c["char_count"],
            })

    fr = sum(c["lang"] == "fr" for c in chunks)
    ar = sum(c["lang"] == "ar" for c in chunks)
    article_count = sum(c["article"] not in (None, "", "preambule") for c in chunks)
    passage_count = len(chunks) - article_count
    lengths = [c["char_count"] for c in chunks]
    short = sum(n < 50 for n in lengths)
    print("========== CHUNKING REPORT ==========")
    print(f"Input records: {len(records)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"FR: {fr} | AR: {ar}")
    print(f"Numbered article chunks: {article_count}")
    print(f"Full-text / preamble passages: {passage_count}")
    print(f"Shortest chunk: {min(lengths, default=0)} chars")
    print(f"Longest chunk: {max(lengths, default=0)} chars")
    print(f"Chunks < 50 chars (to verify): {short}")
    print(f"Generated: {CHUNKS_PATH.relative_to(ROOT)}")
    print(f"Generated: {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
