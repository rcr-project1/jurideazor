"""Tests du découpage de la loi 90-11.
Lancer depuis la racine du projet : python -m pytest tests/ -q
(après avoir lancé : python src/structure/split_loi_90_11.py)
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTS = json.loads((ROOT / "data/processed/articles.json").read_text(encoding="utf-8"))
LOI = [a for a in ARTS if a["texte_id"] == "loi-90-11"]
BY = {a["article"]: a for a in LOI}


def test_no_false_article_heads():
    bad = [a["article"] for a in LOI if re.search(r"\bArt\.?\s*\d+\s*(bis|ter|quater)?\s*[-–—]", a["contenu"])]
    assert bad == [], f"faux débuts d'article dans : {bad}"


def test_all_numbers_present():
    nums = {int(re.match(r"\d+", a["article"]).group()) for a in LOI}
    assert sorted(set(range(1, 159)) - nums) == []


def test_no_duplicates():
    dup = [k for k, v in Counter((a["texte_id"], a["article"]) for a in ARTS).items() if v > 1]
    assert dup == []


def test_ocr_map_applied():
    with (ROOT / "src/structure/ocr_fix_map.csv").open(encoding="utf-8", newline="") as f:
        broken = [r["broken"] for r in csv.DictReader(f)]
    text = " ".join(a["contenu"] + " " + a["titre"] for a in ARTS)
    hits = [b for b in broken if re.search(r"(?<![\w’'])" + re.escape(b) + r"(?![\w’'])", text, re.I)]
    assert hits == [], f"mots cassés restants : {hits}"


def test_list_items_kept():
    assert "contribuer aux efforts" in BY["7"]["contenu"]
    assert "divulgue des informations" in BY["73"]["contenu"]
    assert BY["73-1"]["contenu"].startswith("Dans la détermination de la faute grave")


def test_page_boundaries():
    # le texte qui suit un rappel de page « Art. N » appartient à l'article précédent
    assert BY["100"]["contenu"].endswith("premier et dernier ressort.")
    assert BY["101"]["contenu"].startswith("La durée du mandat des délégués du personnel")
    assert BY["132"]["contenu"].endswith("greffe du tribunal consignataire.")
    assert BY["133"]["contenu"].startswith("La signification de la dénonciation")
    assert "Toutefois, et sous réserve" in BY["157"]["contenu"]
    assert BY["158"]["contenu"].startswith("La présente loi sera publiée")
    assert "5) Gérer les oeuvres sociales" in BY["94"]["contenu"]
    assert BY["95"]["contenu"].startswith("Lorsque l’organisme")


def test_no_title_fragments_at_end():
    assert not BY["14"]["contenu"].endswith("de recrutement")
    assert not BY["61"]["contenu"].endswith("de travail de travail")
    assert not BY["96"]["contenu"].endswith("organes de participation")
    assert not BY["121"]["contenu"].endswith("rang supérieur")


def test_honest_metadata():
    for a in ARTS:
        assert a["date_debut"] is None
        assert a["date_status"] == "non établie"
    assert BY["1"]["version"].startswith("consolidée 1997")


def test_constitution_separate():
    const = [a["article"] for a in ARTS if a["texte_id"].startswith("constitution")]
    assert const == ["54", "55", "56", "57", "58", "59"]