"""Tests for the general French/Arabic article splitter.

Run after: python src/structure/split_articles.py
Then:      python -m pytest tests/test_split_articles.py -q
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "structure"))
import split_articles as splitter  # noqa: E402


def test_french_article_headings():
    sample = "Titre\nArt. 1er. — Premier texte.\nArt. 2. — Deuxième texte."
    path = ROOT / "tests" / "_sample_fr_split.txt"
    path.write_text(sample, encoding="utf-8")
    try:
        result = splitter.split_file(path, "fr")
    finally:
        path.unlink(missing_ok=True)
    assert [x["article"] for x in result] == ["1", "2"]


def test_arabic_article_headings_and_inline_reference():
    sample = (
        "مقدمة طويلة للاختبار تتجاوز خمسين حرفا حتى يتم الاحتفاظ بها في البداية.\n"
        "المادة الأولى : نص المادة الأولى.\n"
        "هذا النص يشير إلى المادة 9 داخل الفقرة ولا يبدأ مادة جديدة.\n"
        "المادة 2 : نص المادة الثانية."
    )
    path = ROOT / "tests" / "_sample_ar_split.txt"
    path.write_text(sample, encoding="utf-8")
    try:
        result = splitter.split_file(path, "ar")
    finally:
        path.unlink(missing_ok=True)
    numbered = [x["article"] for x in result if x["article"] != "preambule"]
    assert numbered == ["1", "2"]
    assert "المادة 9 داخل الفقرة" in result[1]["content"]


def test_loi_90_11_has_all_original_articles_1_to_158():
    output = ROOT / "data" / "processed" / "articles_all.json"
    assert output.exists(), "Run src/structure/split_articles.py first"
    records = json.loads(output.read_text(encoding="utf-8"))
    loi = [
        row for row in records
        if row["lang"] == "fr" and row["source_file"].endswith("loi-90-11.txt")
    ]
    numbers = {str(row["article"]) for row in loi}
    expected = {str(number) for number in range(1, 159)}
    assert expected.issubset(numbers), f"Missing articles: {sorted(expected - numbers)}"
    assert all(row["content"].strip() for row in loi)


def test_no_empty_content_in_output():
    output = ROOT / "data" / "processed" / "articles_all.json"
    assert output.exists(), "Run src/structure/split_articles.py first"
    records = json.loads(output.read_text(encoding="utf-8"))
    assert records
    assert all(row["content"].strip() for row in records)


def test_report_exists():
    report = ROOT / "data" / "processed" / "split_report.csv"
    assert report.exists(), "Run src/structure/split_articles.py first"
