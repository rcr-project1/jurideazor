# Rapport de la semaine 2

**Date :** 18/11/2026. **Dépôt :** `rcr-project1/jurideazor`.
**Référence :** `main` = `5bb3c1b` (fusion PR #11). 5 branches poussées, **non fusionnées** (`git ls-tree <branche> -- <chemin>`).

## 1. Résumé

La semaine 2 devait corriger les manques de la semaine 1, puis collecter, océriser et découper.
**Fait :** 12 numéros collectés (24 PDF), OCR v2 sur 258 pages, 71 textes FR, 67 textes AR, 178 articles découpés (fusionné).
**Non fait :** plan de corpus, filtrage, 8–10 questions avec cache, BM25/E5. Limites : §9.

## 2. Corrections du rapport de la semaine 1

Le rapport de la semaine 1 est inchangé ; ces corrections comptent pour la semaine 2.

| Remarque | Ce qui a été fait | Preuve | Statut |
|---|---|---|---|
| 1. Contributions, noms complets, lignes vides | Noms complets ; 4 tâches vides | `docs/What_you_did.md`, `e3cb909` | Partiel |
| 2. Une seule question citée | 6 questions avec réponses et analyse ; 8–10 questions et erreurs détaillées non faites | `question-test.md` `7d2abc1` ; `Réponses avec sources et références` `0114da6` ; `réponses de LLM sans RAG` `3ce6238` ; `Analyse…` `08fb2e3` (sous `docs/week1/evaluation/`) | Partiel |
| 3. Textes modificatifs par script | 12 numéros collectés, 4 modificatifs ; 96-21, 22-16, 88-07, 90-03, 90-04, LFC 2018 absents | `src/collect/download.py`, `issues_selected.csv` — `feat/collect-hardening` `bdc2af9` | Partiel |
| 4. Numérotation, mots cassés, noms de fichiers | 172 articles = 158 + 14 bis ; 74 corrections OCR ; `gitkeep.ipynb` non renommé | `articles.json`, `ocr_fix_map.csv`, `tests/test_split.py` — `main` `5bb3c1b` | Partiel |

Question hors corpus : la question 6 cite la loi 90-04, absente des deux index (`grep -c "90-04"` = 0).

## 3. État des objectifs

| Objectif | Statut | Preuve | Chiffre |
|---|---|---|---|
| Collecte automatisée | Partiel | `feat/collect-hardening` `bdc2af9` | 12 numéros, 24 PDF |
| OCR + qualité | Fait (CER à refaire) | `feat/ocr-v2` `673701b` | 258 pages |
| Découpage + corrections OCR | Fait | `main` `5bb3c1b` | 178 articles, 9/9 |
| Plan de corpus (Hadil BOUKHALFA) | Non fait | aucun commit | — |
| Filtrage Precision/Recall | Non fait | — | — |
| Cache + 8–10 questions (Rania Halima BENZERAFA) | Non fait | aucun fichier | 6 (semaine 1) |
| BM25 vs E5 (Malak ALIOUAT) | Non fait | — | — |

## 4. Collecte automatisée

`robots.txt` de la JORADP : **HTTP 404** (capture du 2026-11-16, poussée sous l'ancien nom de fichier ; `collection.md` §1). RFC 9309 : un 4xx vaut absence de restriction. L'index UpGrowth (CC BY 4.0) ne donne que les numéros et URL. Client identifié, délai ≥ 3 s, pas de parallélisme. 12 numéros (4 modificatifs + 8 échantillon), 24 PDF. Relance : tout en `skipped`.
Détails : [`collection.md`](collection.md).

## 5. Qualité de l'OCR

Avant 2002 : 10 fichiers scannés, 258 pages. Défaut v1 : colonnes entrelacées. La v2 reconstruit l'ordre de lecture : 191/258 pages à deux colonnes, 656 444 caractères. Contrôle manuel : **3 pages** ; arabe : **1 extrait de 520 caractères** — échantillons trop petits pour généraliser.
Détails : [`ocr_quality.md`](ocr_quality.md).

## 6. Découpage et filtrage

PR #11 (Malak ALIOUAT) fusionnée (`5bb3c1b`) : 178 articles (172 loi 90-11 + 6 Constitution), 9/9 tests, relance sans modification. Provenance : WIPO Lex consolidé 1997, **temporaire** ; source finale JORADP (`data/raw/PROVENANCE.md`). Filtrage non commencé.

## 7. Évaluation du LLM et recherche

Non livré à ce jour. Aucun cache, aucune table d'erreurs par question, aucune mesure Hit@3. Seules les réponses de la semaine 1 existent (§2).

## 8. Contributions

| Membre | Tâches | Fichiers | Commits | Statut |
|---|---|---|---|---|
| Nouha HAROUDI | Collecte, OCR, extraction FR/AR, rapport | `src/collect/`, `src/structure/`, `src/eval/`, `docs/week2/` | `bdc2af9`, `673701b`, `94864fc`, `b00fb37`, `7d13b40` | Livré, non fusionné |
| Malak ALIOUAT | Découpage, corrections OCR, provenance | `split_loi_90_11.py`, `ocr_fix_map.csv`, `tests/test_split.py`, `PROVENANCE.md` | `a6b020d`, `63380eb`, `5bb3c1b` | Livré, fusionné |
| Hadil BOUKHALFA | Plan de corpus | — | — | **Non livré à ce jour (18/11)** |
| Rania Halima BENZERAFA | Cache, questions, table d'erreurs | — | — | **Non livré à ce jour (18/11)** |
| Malak BOUGOFFA | Aucune trace | — | — | Sans contact depuis [À COMPLÉTER] ; tentatives : [À COMPLÉTER] |

Nouha HAROUDI a deux identités Git (`Naho Chan`, `haroudinouha`, même adresse) ; voir `git shortlog -sne --all`.

## 9. Limites et risques

1. 12 numéros collectés, **5 exploités** (1991/068, 1993/001, 1993/002, 1994/020, 1997/003) ; 14 PDF « texte » non convertis (dont 2015/40).
2. 96-21, 22-16, 88-07, 90-03, 90-04, LFC 2018 absents du corpus.
3. Ordonnance 97-02 absente en FR, présente en AR ; idem `loi-91-27`, `loi-91-31`.
4. CER arabe 0,0250 (13/520) **non reproductible** (`src/eval/cer.py`) : non utilisé comme preuve.
5. Aucune `version` ni date : `date_status = "non établie"` (178 articles). `PROVENANCE.md` dit « 1 à 158 » ; la sortie en compte 172.
6. Branches et `docs/week2/` non fusionnées : présents sur GitHub, pas sur `main`.

## 10. Notre calendrier

La plateforme place la recherche en semaine 2. Choix assumé ici : la semaine 1 étant partielle, la semaine 2 corrige, collecte, océrise et découpe ; BM25/E5 et l'arabe passent en semaine 3. Points 1–3 et 6 faits ou partiels ; 4–5 non livrés ; 7 non commencé.

## 11. Usage de l'IA

Scripts écrits avec un agent de code (OpenCode ; modèle `opencode/deepseek-v4.1-flash-free`), relus et testés par l'équipe. Décisions juridiques et chiffres manuels. Nombres recalculés depuis le dépôt. Claude : relecture et planification.

## 12. Question et prochaines étapes

**Question :** recherche (BM25/E5) d'abord, ou textes modificatifs et filtrage ?

| Qui | Quoi |
|---|---|
| Nouha HAROUDI | PDF « texte » (dont 2015/40), CER, fusion des branches |
| Hadil BOUKHALFA | `corpus_index.csv`, échantillon annoté |
| Rania Halima BENZERAFA | cache, 8–10 questions, table d'erreurs |
| Malak ALIOUAT | BM25 vs E5, Hit@3 |
| Malak BOUGOFFA | statut à clarifier |
