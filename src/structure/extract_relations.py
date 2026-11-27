import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTICLES_PATH = ROOT / "data" / "processed" / "articles_all.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "relations.json"
INDEX_PATH = ROOT / "data" / "corpus_index.csv"
GOLD_PATH = ROOT / "eval" / "relation_gold.csv"

# Accept article numbers such as 73, 73-1, 87 bis, and lists such as 22, 23.
ARTICLE_NUMBER = r"\d+(?:\s*(?:-\s*\d+|bis(?:\s+\d+)?|ter|quater|quinquies|sexies))?"
ARTICLE_LIST = (
    rf"{ARTICLE_NUMBER}"
    rf"(?:\s*(?:,|،|;|et|و|à|au|إلى)\s*{ARTICLE_NUMBER})*"
)
LAW_NUMBER = r"\d{2,4}\s*[-–:]\s*\d{1,3}"
FR_LAW = r"(?:loi|ordonnance|décret\s+législatif|décret)"
AR_LAW = r"(?:القانون|الأمر|المرسوم\s+التشريعي|المرسوم)"

FR_RELATIONS = {
    "modifies": re.compile(r"\b(?:modifi\w*|réécrit\w*)\b", re.IGNORECASE),
    "completes": re.compile(r"\b(?:complét\w*|insér\w*|ajout\w*)\b", re.IGNORECASE),
    "repeals": re.compile(r"\b(?:abrog\w*|supprim\w*|annul\w*)\b", re.IGNORECASE),
}

AR_RELATIONS = {
    "modifies": re.compile(r"(?:تعدّل|تعدل|يعدّل|يعدل)"),
    "completes": re.compile(r"(?:تتمّم|تتمم|يتمّم|يتمم|أدرج|تضاف|يضاف)"),
    "repeals": re.compile(r"(?:تلغى|تُلغى|يلغى|يُلغى|تحذف|يحذف)"),
}

# Target article followed by its law citation:
# "L'article 8 du décret n° 85-277 ... est complété"
FR_ARTICLE_THEN_LAW = re.compile(
    rf"(?:l['’]article|les articles|article|articles)\s+"
    rf"(?P<articles>{ARTICLE_LIST})"
    rf"[^.;:()]{{0,120}}?"
    rf"(?:de|du|des)\s+(?:la\s+)?{FR_LAW}\s*"
    rf"(?:n\s*[°ºo]\s*)?(?P<law>{LAW_NUMBER})",
    re.IGNORECASE,
)

AR_ARTICLE_THEN_LAW = re.compile(
    rf"(?:المادة|المواد)\s+"
    rf"(?P<articles>{ARTICLE_LIST})"
    rf"[^؛;.!:()]{{0,120}}?"
    rf"(?:من|في)\s*{AR_LAW}\s*"
    rf"(?:رقم\s*)?(?P<law>{LAW_NUMBER})"
)

# Law citation followed by its target article, for phrases such as
# "la loi n° 90-11 est complétée par un article 73 bis".
FR_LAW_THEN_ARTICLE = re.compile(
    rf"{FR_LAW}\s*(?:n\s*[°ºo]\s*)?(?P<law>{LAW_NUMBER})"
    rf"[^.;:()]{{0,120}}?"
    rf"(?:l['’]article|les articles|un article|une disposition)\s+"
    rf"(?P<articles>{ARTICLE_LIST})",
    re.IGNORECASE,
)

AR_LAW_THEN_ARTICLE = re.compile(
    rf"{AR_LAW}\s*(?:رقم\s*)?(?P<law>{LAW_NUMBER})"
    rf"[^؛;.!:()]{{0,120}}?"
    rf"(?:المادة|المواد)\s+(?P<articles>{ARTICLE_LIST})"
)


def normalize_digits(value):
    """Convert Arabic-Indic digits to Western digits."""
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    western_digits = "0123456789"
    return value.translate(str.maketrans(arabic_digits, western_digits))


def normalize_law_number(value):
    value = normalize_digits(value)
    value = value.replace("–", "-")
    value = value.replace(":", "-")
    return re.sub(r"\s+", "", value)


def normalize_article_numbers(value):
    value = normalize_digits(value)
    value = value.replace("،", ",").replace("و", ",").replace("إلى", "-")
    value = re.sub(r"\s*-\s*", "-", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ,;")


def source_law_from_file(source_file):
    """Get a law number from names such as loi-91-29.txt."""
    stem = Path(source_file).stem
    match = re.search(
        r"(?:loi|ordonnance|decret|décret|legislative-decree|"
        r"decret-legislatif)[-_ ]*(\d{2,4}\s*[-–]\s*\d{1,3})",
        stem,
        re.IGNORECASE,
    )
    if match:
        return normalize_law_number(match.group(1))

    # Keep the filename as a useful identifier when it is not a law-number file.
    return stem


def split_into_clauses(text):
    # Remove stray OCR periods at the start of a line before splitting.
    text = re.sub(r"(?m)^[ \t]*\.\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|[;؛]+", text)
        if part.strip()
    ]


def relation_types_in(clause, language):
    patterns = AR_RELATIONS if language == "ar" else FR_RELATIONS
    return [
        relation
        for relation, pattern in patterns.items()
        if pattern.search(clause)
    ]


def citations_in(clause, language):
    patterns = (
        (AR_ARTICLE_THEN_LAW, AR_LAW_THEN_ARTICLE)
        if language == "ar"
        else (FR_ARTICLE_THEN_LAW, FR_LAW_THEN_ARTICLE)
    )

    citations = []
    for pattern in patterns:
        for match in pattern.finditer(clause):
            citations.append(
                (
                    normalize_law_number(match.group("law")),
                    normalize_article_numbers(match.group("articles")),
                )
            )

    # Avoid duplicate matches when patterns overlap.
    return list(dict.fromkeys(citations))


SOURCE_TARGET_LAW_CONTEXT = {
    "ordonnance-96-21": "90-11",
}


def added_articles_in_clause(clause, language):
    if language == "ar":
        pattern = re.compile(
            rf"(?:تتمم|تتمّم|تُتمم|يتمم).*?"
            rf"بال(?:مادة|مواد)\s*(?P<articles>{ARTICLE_LIST})"
        )
    else:
        pattern = re.compile(
            rf"(?:complét\w*\s+par\s+(?:les\s+)?articles?"
            rf"|ajout\w*.*?\baux articles?)\s+"
            rf"(?P<articles>{ARTICLE_LIST})",
            re.IGNORECASE,
        )

    match = pattern.search(clause)
    if not match:
        return ""

    return normalize_article_numbers(match.group("articles"))

def extract_relations(articles):
    relations = []
    seen = set()

    for article in articles:
        content = article.get("content", "")
        if not isinstance(content, str) or not content.strip():
            continue

        language = article.get("lang", "fr").lower()
        language = "ar" if language.startswith("ar") else "fr"

        source_file = article.get("source_file", "")
        source_law = source_law_from_file(source_file)
        source_name = Path(source_file).stem
        context_law = SOURCE_TARGET_LAW_CONTEXT.get(source_name)

        for clause in split_into_clauses(content):
            relation_types = relation_types_in(clause, language)
            if not relation_types:
                continue

            citations = citations_in(clause, language)
            added_articles = added_articles_in_clause(clause, language)

            for relation in relation_types:
                relation_citations = citations

                # When the text says that an existing article is completed
                # by new articles, attach "completes" to those new articles.
                if relation == "completes" and added_articles:
                    target_law = citations[0][0] if citations else context_law
                    if target_law:
                        relation_citations = [(target_law, added_articles)]

                # Article 18 of Ordinance 96-21 says "the present law"
                # and omits the number 90-11 in that clause.
                if not relation_citations and context_law and added_articles:
                    relation_citations = [(context_law, added_articles)]

                for target_law, target_articles in relation_citations:
                    key = (
                        source_law,
                        str(article.get("article", "")),
                        relation,
                        target_law,
                        target_articles,
                        language,
                    )
                    if key in seen:
                        continue
                    seen.add(key)

                    relations.append({
                        "source_law": source_law,
                        "source_article": str(article.get("article", "")),
                        "relation": relation,
                        "target_law": target_law,
                        "target_articles": target_articles,
                        "lang": language,
                        "evidence": clause[:500],
                    })

    return relations

def normalize_article(value):
    value = normalize_digits(str(value)).strip().lower()
    value = value.replace("–", "-")
    return re.sub(r"\s+", " ", value)


def article_values(value, expected_articles):
    value = normalize_digits(str(value))
    value = value.replace("،", ",").replace("و", ",")
    parts = re.split(
        r"\s*(?:,|;|\bet\b|\band\b)\s*",
        value,
        flags=re.IGNORECASE,
    )

    result = set()

    for part in parts:
        article = normalize_article(part)
        if not article:
            continue

        # Keep exact numbers such as "73-1" and "56 bis 1".
        if article in expected_articles:
            result.add(article)
            continue

        # Expand ranges such as "22 à 26" when the reference lists
        # each article separately.
        match = re.fullmatch(
            r"(\d{1,3})\s*(?:à|to|-)\s*(\d{1,3})",
            article,
        )
        if match:
            start, end = map(int, match.groups())
            if start <= end and end - start <= 100:
                result.update(
                    str(number)
                    for number in range(start, end + 1)
                    if str(number) in expected_articles
                )
                continue

        result.add(article)

    return result


def evaluate_relations(extracted):
    with GOLD_PATH.open(encoding="utf-8", newline="") as file:
        gold_rows = list(csv.DictReader(file))

    expected = set()
    expected_articles_by_pair = {}
    scored_pairs = set()

    for row in gold_rows:
        source_law = normalize_law_number(row["source_law"])
        target_law = normalize_law_number(row["target_law"])
        relation = row["relation"].strip()
        pair = (source_law, target_law)

        articles = [
            normalize_article(article)
            for article in row["target_articles"].split(";")
            if article.strip()
        ]

        scored_pairs.add(pair)
        expected_articles_by_pair.setdefault(pair, set()).update(articles)

        for article in articles:
            expected.add((source_law, relation, target_law, article))

    found = set()

    for item in extracted:
        source_law = normalize_law_number(item.get("source_law", ""))
        target_law = normalize_law_number(item.get("target_law", ""))
        pair = (source_law, target_law)

        if pair not in scored_pairs:
            continue

        articles = article_values(
            item.get("target_articles", ""),
            expected_articles_by_pair[pair],
        )

        for article in articles:
            found.add((
                source_law,
                item.get("relation", "").strip(),
                target_law,
                article,
            ))

    correct = expected & found
    precision = len(correct) / len(found) if found else 0
    recall = len(correct) / len(expected) if expected else 0

    print(f"Reference relations: {len(expected)}")
    print(f"Extracted relations scored: {len(found)}")
    print(f"Correct matches: {len(correct)}")
    print(f"Precision: {precision:.1%}")
    print(f"Recall: {recall:.1%}")

    print("\nMissed reference relations:")
    for relation in sorted(expected - found):
        print(" ", relation)

    print("\nExtracted relations not in the reference:")
    for relation in sorted(found - expected):
        print(" ", relation)

def main():
    if not ARTICLES_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {ARTICLES_PATH}")

    with ARTICLES_PATH.open(encoding="utf-8") as file:
        articles = json.load(file)

    relations = extract_relations(articles)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(relations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Articles read: {len(articles)}")
    print(f"Relations found: {len(relations)}")
    print(f"Generated: {OUTPUT_PATH.relative_to(ROOT)}")
    evaluate_relations(relations)


if __name__ == "__main__":
    main()