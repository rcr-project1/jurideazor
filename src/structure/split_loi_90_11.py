"""Nettoyage et découpage de la loi 90-11 en articles.

Entrée :
    data/raw/loi_90_11.txt

Fichiers de sortie :
    data/processed/articles.json
    data/processed/loi_90_11_clean.txt
    data/processed/rapport_decoupage.txt

Lancement depuis la racine du projet :
    python src/structure/split_loi_90_11.py
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path


# ============================================================
# 0. CHEMINS ET CONFIGURATION
# ============================================================

RAW = Path("data/raw/loi_90_11.txt")
OUT = Path("data/processed")
OCR_MAP = Path("src/structure/ocr_fix_map.csv")

SOURCE_URL = "https://www.wipo.int/wipolex/fr/legislation/details/14834"


# ============================================================
# 1. LECTURE DU FICHIER SOURCE
# ============================================================

if not RAW.exists():
    raise FileNotFoundError(
        f"Fichier source introuvable : {RAW}"
    )

text = RAW.read_text(encoding="utf-8")
text = text.replace("\r\n", "\n").replace("\r", "\n")

lines = [line.strip() for line in text.split("\n")]

# Chercher le début de la loi.
try:
    start = next(
        i for i, line in enumerate(lines)
        if line.startswith("LIVRE PREMIER")
    )
except StopIteration:
    raise ValueError(
        "Le début de la loi 'LIVRE PREMIER' est introuvable."
    )

# Supprimer les numéros de page et les en-têtes répétitifs.
NOISE = re.compile(
    r"^(\d{1,3}|Relations de travaill?|"
    r"Loi n° 90-11 du 21/04/1990)$",
    re.IGNORECASE
)

pre = [
    line for line in lines[:start]
    if line and not NOISE.match(line)
]

body = [
    line for line in lines[start:]
    if line and not NOISE.match(line)
]


# ============================================================
# 2. FONCTIONS DE NETTOYAGE OCR
# ============================================================

def tokens(sentence):
    """Extraire les mots d'un texte."""
    return re.findall(
        r"[A-Za-zÀ-ÿ’']+",
        sentence.lower()
    )


# Les mots qui apparaissent au milieu des lignes
# servent à reconnaître certains mots coupés.
inline = Counter(
    token
    for line in body
    for token in tokens(line)[1:-1]
)

joined_words = []


def merge_lines(lines_to_merge):
    """
    Joindre les lignes et recoller certains mots
    coupés à la fin d'une ligne.
    """

    result = ""

    for line in lines_to_merge:

        if not result:
            result = line
            continue

        previous_tokens = tokens(result)
        current_tokens = tokens(line)

        previous_word = (
            previous_tokens[-1]
            if previous_tokens else ""
        )

        current_word = (
            current_tokens[0]
            if current_tokens else ""
        )

        should_join = (
            previous_word
            and current_word
            and result[-1].isalpha()
            and line[0].islower()
            and inline[previous_word + current_word] >= 1
            and inline[previous_word] == 0
        )

        if should_join:
            result += line
            joined_words.append(
                previous_word + current_word
            )
        else:
            result += " " + line

    result = re.sub(r"\s+", " ", result).strip()

    # Correction d'une erreur OCR fréquente.
    result = re.sub(
        r"\bl er\b",
        "1er",
        result,
        flags=re.IGNORECASE
    )

    return result


# ============================================================
# 3. CHARGEMENT DU DICTIONNAIRE OCR
# ============================================================

def load_ocr_fixes():
    """
    Lire les corrections depuis ocr_fix_map.csv.

    Le fichier doit contenir deux colonnes :
        broken,fixed
    """

    if not OCR_MAP.exists():
        raise FileNotFoundError(
            f"Fichier OCR introuvable : {OCR_MAP}\n"
            "Crée d'abord le fichier ocr_fix_map.csv."
        )

    fixes = []

    with OCR_MAP.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames or not {
            "broken", "fixed"
        }.issubset(reader.fieldnames):
            raise ValueError(
                "Le CSV doit contenir les colonnes "
                "'broken' et 'fixed'."
            )

        for row in reader:
            broken = (row.get("broken") or "").strip()
            fixed = (row.get("fixed") or "").strip()

            if broken and fixed:
                fixes.append((broken, fixed))

    return fixes


OCR_FIXES = load_ocr_fixes()


# Corrections supplémentaires observées pendant l'audit du découpage.
# Les corrections incertaines ne sont ajoutées ici que si elles sont validées.
EXTRA_OCR_FIXES = [
    ("auto risation", "autorisation"),
    ("insa lubres", "insalubres"),
    ("étran gers", "étrangers"),
    ("augmen tation", "augmentation"),
    ("dépas ser", "dépasser"),
    ("déter minées", "déterminées"),
    ("car rière", "carrière"),
    ("dcs parties", "des parties"),
    ("règle ments", "règlements"),
    ("profession nels", "professionnels"),
    ("approba tion", "approbation"),
    ("consta tée", "constatée"),
    ("en gendrer", "engendrer"),
    ("consul tés", "consultés"),
    ("l’au torise", "l'autorise"),
]


def apply_ocr_fixes(sentence):
    """Appliquer les corrections OCR du CSV puis les corrections sûres."""

    all_fixes = OCR_FIXES + EXTRA_OCR_FIXES

    for broken, fixed in all_fixes:

        pattern = (
            r"(?<!\w)"
            + re.escape(broken)
            + r"(?!\w)"
        )

        sentence = re.sub(
            pattern,
            lambda match, fixed=fixed: (
                fixed[0].upper() + fixed[1:]
                if match.group(0)[0].isupper()
                else fixed
            ),
            sentence,
            flags=re.IGNORECASE
        )

    return sentence


# ============================================================
# 4. RECONNAISSANCE DES ARTICLES
# ============================================================

ART = re.compile(
    r"^Art(?:icle)?\.?\s*"
    r"(\d+|ler|1er)"
    r"(?:-(\d+))?"
    r"\s*(bis|ter|quater)?\.?"
    r"\s*([-–—])?\s*(.*)$",
    re.IGNORECASE
)

RANK = {
    "": 0,
    "bis": 1,
    "ter": 2,
    "quater": 3
}


def parse(line):
    """Analyser une ligne qui pourrait commencer un article."""

    match = ART.match(line)

    if not match:
        return None

    number_text = match.group(1).lower()

    number = (
        1
        if number_text in ("ler", "1er")
        else int(number_text)
    )

    suffix_number = (
        int(match.group(2))
        if match.group(2)
        else RANK[(match.group(3) or "").lower()]
    )

    label = str(number)

    if match.group(2):
        label += f"-{match.group(2)}"

    if match.group(3):
        label += f" {match.group(3).lower()}"

    spaced_dash = bool(
        re.match(
            r"^Art(?:icle)?\.?\s*"
            r"[\w-]+(?:\s+\w+\.?)?\s[-–—]\s",
            line,
            re.IGNORECASE
        )
    )

    return (
        (number, suffix_number),
        label,
        match.group(5),
        match.group(4) is not None,
        spaced_dash
    )


# ============================================================
# 5. IDENTIFICATION DES FAUX DÉBUTS D'ARTICLES
# ============================================================

# Ces lignes sont des faux titres confirmés dans le guide.
# On retire uniquement le faux titre et on garde le texte après.
FALSE_HEADS = [
    re.compile(
        r"^Art(?:icle)?\.?\s*9\s*[-–—]\s*contribuer\b",
        re.IGNORECASE
    ),
    re.compile(
        r"^Art(?:icle)?\.?\s*32\s*[-–—]\s*prévenir\b",
        re.IGNORECASE
    ),
    re.compile(
        r"^Art(?:icle)?\.?\s*73\s*[-–—]\s*au travail "
        r"à temps partiel\b",
        re.IGNORECASE
    ),
    # Faux titre dans la liste des fautes graves de l'article 73.
    # Le texte après ce marqueur reste dans l'article 73.
    re.compile(
        r"^Art(?:icle)?\.?\s*73-1\s*[-–—]\s*divulgue\b",
        re.IGNORECASE
    ),
]


def is_false_head(line):
    return any(
        pattern.match(line)
        for pattern in FALSE_HEADS
    )


# ============================================================
# 6. SÉLECTION DES VRAIS DÉBUTS D'ARTICLES
# ============================================================

candidates = []

for i, line in enumerate(body):

    # Ne pas considérer les faux titres comme des articles.
    if is_false_head(line):
        continue

    parsed = parse(line)

    if parsed and parsed[3]:
        candidates.append(
            (
                i,
                parsed[0],
                parsed[1],
                parsed[2],
                parsed[4]
            )
        )


# Plus longue suite croissante des numéros d'articles.
best = []
previous = [-1] * len(candidates)

for j, candidate in enumerate(candidates):

    best.append(1 + 0.5 * candidate[4])

    for i in range(j):

        if candidates[i][1] < candidate[1]:

            score = (
                best[i]
                + 1
                + 0.5 * candidate[4]
            )

            if score > best[j]:
                best[j] = score
                previous[j] = i


accepted = []

if candidates:

    j = max(
        range(len(candidates)),
        key=lambda x: best[x]
    )

    while j != -1:
        accepted.append(j)
        j = previous[j]

    accepted = [
        candidates[j]
        for j in reversed(accepted)
    ]


acc = {
    candidate[0]: candidate
    for candidate in accepted
}

rejected = [
    (i, body[i])
    for i, *_rest in candidates
    if i not in acc
]


# ============================================================
# 7. DÉCOUPAGE DES ARTICLES
# ============================================================

HEAD = re.compile(
    r"^(LIVRE|TITRE|Chapitre|Section)\s+"
    r"([IVX\d]+|PREMIER|ler)\s*$",
    re.IGNORECASE
)

context = {
    "livre": "",
    "titre": "",
    "chapitre": "",
    "section": ""
}

articles = []
current = None

markers_used = []
markers_dropped = []
false_heads_removed = []

want_title = None
title_lines = 0
accepted_indices = sorted(acc)


def next_accepted_key(index):
    """Retourner le prochain numéro d'article accepté."""

    for accepted_index in accepted_indices:

        if accepted_index > index:
            return acc[accepted_index][1]

    return None


for i, line in enumerate(body):

    # --------------------------------------------------------
    # A. Détecter les titres, chapitres et sections.
    # --------------------------------------------------------

    heading = HEAD.match(line)

    if heading:

        kind = heading.group(1).lower()
        context[kind] = line

        reset_fields = {
            "livre": ["titre", "chapitre", "section"],
            "titre": ["chapitre", "section"],
            "chapitre": ["section"],
            "section": []
        }

        for field in reset_fields[kind]:
            context[field] = ""

        want_title = kind
        title_lines = 0
        continue

    # Ajouter le texte du titre qui se trouve sur la ligne suivante.
    if want_title and not ART.match(line):

        # Un titre peut occuper jusqu'à 3 lignes ; sinon la fin du titre
        # se retrouve à tort à la fin de l'article précédent.
        context[want_title] += (" – " if title_lines == 0 else " ") + line
        title_lines += 1

        if title_lines >= 3:
            want_title = None

        continue

    want_title = None

    # --------------------------------------------------------
    # B. Traiter les faux titres confirmés.
    # --------------------------------------------------------

    if is_false_head(line):

        parsed = parse(line)

        if parsed and current:

            remaining_text = parsed[2].strip()

            if remaining_text:
                current["lines"].append(remaining_text)

            false_heads_removed.append(line)

        continue

    # --------------------------------------------------------
    # C. Traiter les vrais débuts d'articles acceptés.
    # --------------------------------------------------------

    if i in acc:

        _, key, label, rest, _ = acc[i]

        if current and current["key"] == key:

            current["lines"].append(rest)

        else:

            current = {
                "key": key,
                "article": label,
                "lines": [rest],
                **{
                    k: v
                    for k, v in context.items()
                    if k != "livre"
                }
            }

            articles.append(current)

        continue

    # --------------------------------------------------------
    # D. Rappels de page : "Art. 5" seul sur une ligne.
    # --------------------------------------------------------
    # En haut d'une page, le texte d'origine répète le numéro de l'article
    # qui commence plus bas sur la page. Ce n'est PAS un début d'article :
    # le texte qui suit est la suite de l'article précédent.

    parsed = parse(line)

    if parsed and not parsed[3] and not parsed[2]:

        markers_dropped.append(f"ligne {i}: {line}")
        continue

    # --------------------------------------------------------
    # E. Garder les autres lignes dans l'article courant.
    # --------------------------------------------------------

    if current:
        current["lines"].append(line)


# ============================================================
# 8. EXTRACTION DES EXTRAITS DE LA CONSTITUTION
# ============================================================

constitution = []
current_constitution = None

for line in pre:

    parsed = parse(line)

    if parsed and parsed[3]:

        current_constitution = {
            "article": parsed[1],
            "lines": [parsed[2]]
        }

        constitution.append(current_constitution)

    elif current_constitution:

        current_constitution["lines"].append(line)


# ============================================================
# 9. FINALISATION DES TEXTES
# ============================================================

def finish(article):
    """Joindre les lignes et appliquer les corrections OCR."""

    content = merge_lines(article.pop("lines"))
    content = apply_ocr_fixes(content)

    # Certains débuts d’articles sont en minuscule dans l’OCR (ex. article 130).
    if content:
        content = content[0].upper() + content[1:]

    article["texte"] = content
    article.pop("key", None)

    return article


records = []

# Articles de la loi 90-11.
for article in articles:

    article = finish(article)

    records.append({
        "texte_id": "loi-90-11",
        "article": article["article"],
        "titre": apply_ocr_fixes(article["titre"]),
        "chapitre": apply_ocr_fixes(article["chapitre"]),
        "section": apply_ocr_fixes(article["section"]),
        "contenu": article["texte"],

        # Le texte est une version consolidée de 1997.
        "version": "consolidée 1997 (WIPO)",
        "date_debut": None,
        "date_status": "non établie",
        "date_fin": None,

        "source_url": SOURCE_URL
    })


# Extraits de la Constitution.
for constitution_article in constitution:

    content = merge_lines(
        constitution_article["lines"]
    )

    content = apply_ocr_fixes(content)

    records.append({
        "texte_id": "constitution-1996-extraits",
        "article": constitution_article["article"],
        "titre": "",
        "chapitre": "",
        "section": "",
        "contenu": content,
        "version": "1996",
        "date_debut": None,
        "date_status": "non établie",
        "date_fin": None,
        "source_url": SOURCE_URL
    })


# ============================================================
# 10. CRÉATION DES FICHIERS DE SORTIE
# ============================================================


# Les frontières entre articles sont gérées par les règles A et D (section 7).

OUT.mkdir(
    parents=True,
    exist_ok=True
)

# Fichier JSON.
json_path = OUT / "articles.json"

json_path.write_text(
    json.dumps(
        records,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


# Fichier texte propre.
clean_path = OUT / "loi_90_11_clean.txt"

law_records = [
    record
    for record in records
    if record["texte_id"] == "loi-90-11"
]

clean_content = "\n\n".join(
    f"Art. {record['article']} - {record['contenu']}"
    for record in law_records
)

clean_path.write_text(
    clean_content,
    encoding="utf-8"
)


# ============================================================
# 11. GÉNÉRATION DU RAPPORT
# ============================================================

numbers = sorted({
    int(re.match(r"\d+", record["article"]).group())
    for record in law_records
})

short_articles = [
    record["article"]
    for record in law_records
    if len(record["contenu"]) < 60
]

rare_words = Counter()

for record in law_records:

    for token in tokens(record["contenu"]):

        if inline[token] == 0 and len(token) >= 3:
            rare_words[token] += 1


missing_numbers = sorted(
    set(range(1, 159)) - set(numbers)
)

suffix_articles = [
    record["article"]
    for record in law_records
    if not record["article"].isdigit()
]

constitution_articles = [
    record["article"]
    for record in records
    if record["texte_id"].startswith("constitution")
]


# Alertes de contrôle : elles signalent des cas à comparer au texte source.
# Le script ne modifie pas automatiquement ces passages, car leur correction
# exige de vérifier la version originale de la loi.
audit_warnings = []
END_OK = (".", ";", ":", "!", "?", "»", ")")

for record in law_records:
    content = record["contenu"].rstrip()
    label = record["article"]

    if content and not content.endswith(END_OK):
        audit_warnings.append(
            f"Article {label} : se termine sans ponctuation finale "
            f"(« …{content[-40:]} ») ; fragment de titre ou texte coupé ?"
        )

    if content and content[0].islower():
        audit_warnings.append(
            f"Article {label} : commence par une minuscule "
            f"(« {content[:40]}… ») ; continuation de l'article précédent ?"
        )

report = [

    "========== RAPPORT DE DECOUPAGE ==========",

    "",

    f"Articles de la loi 90-11 trouvés : {len(law_records)}",

    f"Numéros distincts : {len(numbers)}",

    f"Numéros manquants entre 1 et 158 : {missing_numbers}",

    f"Articles avec suffixe : {suffix_articles}",

    f"Extraits de la Constitution : {constitution_articles}",

    "",

    "---------- CORRECTIONS ----------",

    f"Mots recollés automatiquement : {len(joined_words)}",

    f"Corrections OCR chargées depuis le CSV : {len(OCR_FIXES)}",
    f"Corrections OCR supplémentaires sûres : {len(EXTRA_OCR_FIXES)}",

    f"Faux titres retirés : {len(false_heads_removed)}",

    *[
        f"  - {line}"
        for line in false_heads_removed
    ],

    "",

    "---------- ALERTES À VÉRIFIER DANS LA SOURCE ----------",
    *[
        f"  - {warning}"
        for warning in audit_warnings
    ],
    "",
    "---------- ARTICLES COURTS ----------",

    f"Articles de moins de 60 caractères : {short_articles}",

    "",

    "---------- CANDIDATS REJETÉS ----------",

    *[
        f"  ligne {i}: {line[:120]}"
        for i, line in rejected
    ],

    "",

    "---------- MARQUEURS SEULS ----------",

    "Rappels de page « Art. N » ignorés "
    "(la suite du texte reste dans l'article précédent) :",

    *[
        f"  - {marker}"
        for marker in markers_dropped
    ],

    "",

    "---------- MOTS RARES À VÉRIFIER ----------",

    ", ".join(sorted(rare_words)[:150]),

    "",

    "========== FIN DU RAPPORT =========="
]


report_path = OUT / "rapport_decoupage.txt"

report_path.write_text(
    "\n".join(report),
    encoding="utf-8"
)


# ============================================================
# 12. AFFICHAGE DU RÉSULTAT
# ============================================================

print("\n========== TERMINÉ ==========")

print(
    f"Articles de la loi trouvés : {len(law_records)}"
)

print(
    f"Numéros manquants : {missing_numbers}"
)

print(
    f"Faux titres retirés : {len(false_heads_removed)}"
)

print(
    f"Corrections OCR chargées : {len(OCR_FIXES)} "
    f"(+ {len(EXTRA_OCR_FIXES)} corrections supplémentaires)"
)

if audit_warnings:
    print("\nALERTES : vérifier ces passages dans le texte source :")
    for warning in audit_warnings:
        print(f"- {warning}")

print("\nFichiers générés :")

print(f"- {json_path}")
print(f"- {clean_path}")
print(f"- {report_path}")

print("\nVérifie le rapport et le contenu des articles.")