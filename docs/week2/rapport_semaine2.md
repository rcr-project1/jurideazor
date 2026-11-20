# Rapport de la semaine 2

**Date :** 20/11/2026 (mise à jour). **Dépôt :** `rcr-project1/jurideazor`.
**Référence :** `main` = `c0cecec` (PR #17, #19, #21–#23 fusionnées). 5 branches poussées, **non fusionnées** (`feat/collect-hardening`, `feat/ocr-v2`, `feat/fr-pipeline`, `feat/ar-pipeline`, `docs/week2`) ; PR #12–#16 ouvertes.

## 1. Résumé

La semaine 2 devait corriger les manques de la semaine 1, puis collecter, océriser et découper.
**Fait :** 18 numéros collectés (36 PDF : 18 scan, 18 texte), OCR v2 sur **529 pages** (9 numéros scan, 18 fichiers FR+AR), **126 textes FR** (43 numérotés), **57 textes AR** (31 numérotés), 178 articles découpés (fusionné).
Source des 178 articles : texte WIPO temporaire, pas la sortie OCR. Plan de corpus (Hadil, PR #17) fusionné.
**Non fait :** filtrage, 8–10 questions avec cache, BM25/E5. Extraction des 6 PDF « texte » (2015, 2017, 2022) à faire. Limites : §9.

## 2. Corrections du rapport de la semaine 1

Le rapport de la semaine 1 est inchangé ; ces corrections comptent pour la semaine 2.

| Remarque | Ce qui a été fait | Preuve | Statut |
|---|---|---|---|
| 1. Contributions, noms complets, lignes vides | Noms complets ; 4 tâches vides | `docs/What_you_did.md`, `e3cb909` | Partiel |
| 2. Une seule question citée | 6 questions avec réponses et analyse ; 8–10 questions et erreurs détaillées non faites | `question-test.md` `7d2abc1` ; `Réponses avec sources et références` `0114da6` ; `réponses de LLM sans RAG` `3ce6238` ; `Analyse…` `08fb2e3` (sous `docs/week1/evaluation/`) | Partiel |
| 3. Textes modificatifs par script | 18 numéros collectés (10 planifiés + 8 échantillon), 10 modificatifs ; les 6 numéros de PR #17 sont collectés le 19/11 (4 scan, 2 texte) : OCR et extraction encore à faire | `src/collect/download.py`, `issues_selected.csv` — `feat/collect-hardening` `2231cad` ; `data/corpus_index.csv` — PR #17 | Partiel |
| 4. Numérotation, mots cassés, noms de fichiers | 172 articles = 158 + 14 bis ; 73 corrections OCR valides (75 lignes : en-tête + 74 lignes de données dont une vide) + 15 corrections supplémentaires dans le script ; `gitkeep.ipynb` non renommé (notebook de Rania, à renommer par elle) | `articles.json`, `ocr_fix_map.csv`, `tests/test_split.py` — `main` `5bb3c1b` | Partiel |

Question hors corpus : la question 6 cite la loi 90-04 ; son PDF est collecté le 19/11 (`1990/06`), texte pas encore extrait.

## 3. État des objectifs

| Objectif | Statut | Preuve | Chiffre |
|---|---|---|---|
| Collecte automatisée | Partiel | `feat/collect-hardening` `c890d9a` | 18 numéros, 36 PDF (18 scan, 18 texte) |
| OCR + qualité | Fait (CER à refaire) | `feat/ocr-v2` `590c503` | 529 pages (18 fichiers, 9 numéros) |
| Découpage + corrections OCR | Fait | `main` `5bb3c1b` | 178 articles, 9/9 |
| Plan de corpus (Hadil BOUKHALFA) | Fusionné | PR #17 `c0cecec` | 12 textes, 20 documents |
| Filtrage Precision/Recall | Non fait | — | — |
| Cache + 8–10 questions (Rania Halima BENZERAFA) | Non fait | aucun fichier | 6 (semaine 1) |
| BM25 vs E5 (Malak ALIOUAT) | Non fait | — | — |

Source des 178 articles : texte WIPO temporaire, pas la sortie OCR.

## 4. Collecte automatisée

`robots.txt` de la JORADP : **HTTP 404** (capture du 2026-11-16, `docs/week2/robots_404_2026-11-16.png` ; `collection.md` §1). RFC 9309 : un 4xx vaut absence de restriction. L'index UpGrowth (CC BY 4.0) ne donne que les numéros et URL. Client identifié, délai ≥ 3 s, pas de parallélisme. 18 numéros (10 planifiés + 8 échantillon), 36 PDF (18 scan, 18 texte). Relance : tout en `skipped`.
Détails : [`collection.md`](collection.md).

## 5. Qualité de l'OCR

Avant 2002 : 18 fichiers scannés (9 numéros × FR/AR), **529 pages**. Défaut v1 : colonnes entrelacées. La v2 reconstruit l'ordre de lecture ; correction supplémentaire le 20/11 : lignes dupliquées éliminées (centre de ligne au lieu de marges chevauchantes), padding arabe. Résultat : ~1 491 000 caractères, 0 page vide. Contrôle manuel : **3 pages** ; arabe : **1 extrait de 520 caractères** — échantillons trop petits pour généraliser.
Détails : [`ocr_quality.md`](ocr_quality.md).

## 6. Découpage et filtrage

PR #11 (Malak ALIOUAT) fusionnée (`5bb3c1b`) : 178 articles (172 loi 90-11 + 6 Constitution), 9/9 tests, relance sans modification. Provenance : WIPO Lex consolidé 1997, **temporaire** ; PDF JORADP original collecté le 19/11 (`1990/17`), extraction à faire (`data/raw/PROVENANCE.md`).

Extraction JORADP (OCR v2) — `feat/fr-pipeline` `997db23` : **126 textes FR** (43 numérotés, 83 non numérotés) ; `feat/ar-pipeline` `eaa0b96` : **57 textes AR** (31 numérotés). Textes clés retrouvés : loi-91-29, ordonnance-97-02/03/04, décret-94-03. Filtrage non commencé.

## 7. Évaluation du LLM et recherche

Non livré à ce jour. Aucun cache, aucune table d'erreurs par question, aucune mesure Hit@3. Seules les réponses de la semaine 1 existent (§2).

## 8. Contributions

| Membre | Tâches | Fichiers | Commits | Statut |
|---|---|---|---|---|
| Nouha HAROUDI | Collecte, OCR, extraction FR/AR, rapport | `src/collect/`, `src/structure/`, `src/eval/`, `docs/week2/` | `c890d9a`, `590c503`, `997db23`, `eaa0b96`, `docs/week2` | Livré, non fusionné |
| Malak ALIOUAT | Découpage, corrections OCR, provenance | `split_loi_90_11.py`, `ocr_fix_map.csv`, `tests/test_split.py`, `PROVENANCE.md` | `a6b020d`, `63380eb`, `5bb3c1b` | Livré, fusionné |
| Hadil BOUKHALFA | Plan de corpus, index, échantillon | `data/corpus_index.csv`, `docs/week2/corpus_plan.md`, `eval/relevance_sample.csv` | `b26afee` | Fusionné (PR #17) |
| Rania Halima BENZERAFA | Questions 11–16, analyse des erreurs, notebook | `docs/week1/evaluation/` (3 fichiers) | `1237690`, `212acb9`, `018d6b8` | Livré (PR #24–#26), non fusionné |
| Malak BOUGOFFA | Retirée du groupe à sa demande | — | — | Retrait demandé le 18/11/2026 (appel) ; enseignant informé le 18/11/2026, retrait effectué par l'enseignant |

Nouha HAROUDI a deux identités Git (`Naho Chan`, `haroudinouha`, même adresse) ; voir `git shortlog -sne --all`.

## 9. Limites et risques

1. 18 numéros collectés, **9 exploités** (tous les scans : 1988/004, 1990/006, 1990/017, 1991/068, 1993/001, 1993/002, 1994/020, 1996/043, 1997/003) ; **6 PDF « texte » non convertis** (3 numéros : 2015/040, 2017/076, 2022/049 × FR/AR) — besoin d'un extracteur `pymupdf.get_text()`, pas de Tesseract.
2. 96-21, 22-16, 88-07, 90-03, 90-04, LFC 2018 : PDF collectés, OCR fait pour les scans ; extraction des textes individuels à refaire avec le texte v2.
3. Ordonnance 97-02 **extraite** dans les deux langues (FR : `997db23`, AR : `eaa0b96`). Décret 94-03 (AR) reste partiellement garbled dans le texte OCR v2 (heading noisy mais récupéré en FR). L'ordonnance 97-01 n'est extraite dans aucune des deux langues.
4. CER arabe 0,0250 (13/520) **non reproductible** (`src/eval/cer.py`) : non utilisé comme preuve.
5. Dates de mise en vigueur absentes : `date_status = "non établie"` (178 articles). `PROVENANCE.md` annonce « 1 à 158 » (numéros de la version consolidée) ; `articles.json` contient 172 enregistrements = 158 numéros + 14 articles suffixés (bis/ter/quater) : écart attendu, pas une contradiction.
6. 6 branches et `docs/week2/` non fusionnées : présents sur GitHub, pas sur `main`.

## 10. Notre calendrier

La plateforme place la recherche en semaine 2. Choix assumé ici : la semaine 1 étant partielle, la semaine 2 corrige, collecte, océrise et découpe ; BM25/E5 et l'arabe passent en semaine 3. Points 1–3 et 6 faits ou partiels ; 4–5 non livrés ; 7 non commencé.

## 11. Usage de l'IA

Scripts écrits avec un agent de code (OpenCode ; modèle `opencode/deepseek-v4.1-flash-free`), relus et testés par l'équipe. Décisions juridiques et chiffres manuels. Nombres recalculés depuis le dépôt. Claude : relecture et planification.

## 12. Question et prochaines étapes

**Question :** recherche (BM25/E5) d'abord, ou textes modificatifs et filtrage ?

| Qui | Quoi |
|---|---|
| Nouha HAROUDI | Extracteur PDF « texte » (2015/2017/2022), re-extraction FR/AR avec texte v2, fusion des branches |
| Hadil BOUKHALFA | Vérification corpus_index après fusion |
| Rania Halima BENZERAFA | Fusionner PR #24–#26, compléter cache et table d'erreurs |
| Malak ALIOUAT | BM25 vs E5, Hit@3 |
