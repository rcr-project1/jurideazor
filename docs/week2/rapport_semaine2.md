# Rapport de la semaine 2

**Date :** 20/11/2026. **Dépôt :** `rcr-project1/jurideazor`. **Branche :** `main` = `3ff61d5`.

## 1. Résumé

| Fait | Chiffre |
|------|---------|
| Collecte automatisée (JORADP) | 36 PDF (18 scan + 18 texte) |
| OCR v2 (scans uniquement) | 529 pages, 18 fichiers, 0 page vide |
| Nettoyage FR + AR | 18 fichiers (9 FR + 9 AR) |
| Extraction FR | 126 textes (43 numérotés) |
| Extraction AR | 57 textes (31 numérotés) |
| Découpage loi 90-11 | 178 articles (172 + 6 Constitution) |
| Extracteur PDF texte | Script prêt, non exécuté |
| Plan de corpus | 12 textes indexés |
| Évaluation LLM sans RAG | 16 questions (Q1–Q16) |

**Non fait :** BM25 vs E5, Hit@3, filtrage Precision/Recall, cache LLM.

## 2. Corrections de la semaine 1

| Remarque du prof | Action | Statut |
|------------------|--------|--------|
| Contributions incomplètes | Noms complets ajoutés | Fait |
| Une seule question citée | 16 questions avec réponses et analyse d'erreurs | Fait |
| Textes modificatifs par script | 12 textes identifiés dans `corpus_index.csv`, 36 PDF collectés | Fait |
| Mots cassés OCR | 73 corrections CSV + 15 dans le script, 178 articles propres | Fait |

## 3. Pipeline de données

### 3.1 Collecte (`src/collect/`)

**Quoi :** téléchargement automatique des PDF depuis le site JORADP.  
**Pourquoi :** rassembler le corpus de base (loi 90-11 + ses 11 textes modificatifs).  
**Comment :** `download.py` lit `corpus_index.csv`, télécharge chaque PDF, vérifie le SHA256.  
**Résultat :** 36 PDF (18 FR + 18 AR), 0 erreur. `inspect_pdfs.py` les classe en 18 scan (1988–1997) et 18 texte (2005–2022).  
**Où :** `data/raw/joradp/pdf/`, `data/processed/pdf_report.csv`, `data/processed/downloads_manifest.csv`.  
**Branche :** `feat/collect-hardening` → fusionnée (PR #14).

### 3.2 OCR v2 (`src/collect/ocr_columns.py`)

**Quoi :** conversion des 18 PDF scannés en texte brut.  
**Pourquoi :** les PDF avant 2002 sont des images, pas du texte extractible.  
**Comment :** Tesseract avec détection d'agencement en deux colonnes — chaque ligne assignée à sa colonne par son centre, padding 1 % pour l'arabe.  
**Résultat :** 529 pages, ~1 491 000 caractères, 0 page vide.  
**Où :** `data/raw/joradp/text_v2/` (gitignored — régénérable).  
**Branche :** `feat/ocr-v2` → fusionnée (PR #13).

### 3.3 Nettoyage (`src/structure/clean_text.py`, `clean_ar.py`)

**Quoi :** suppression des artefacts OCR (en-têtes, numéros de page, mots coupés, caractères parasites).  
**Pourquoi :** le texte OCR brut contient des en-têtes répétitifs et des coupures de mots en fin de ligne.  
**Résultat :** 9 fichiers FR + 9 fichiers AR nettoyés.  
**Où :** `data/processed/text_clean/` (gitignored — régénérable).

### 3.4 Extraction (`src/structure/extract_texts.py`, `extract_texts_ar.py`)

**Quoi :** séparation de chaque gazette en textes juridiques individuels (loi, décret, arrêté, ordonnance).  
**Pourquoi :** chaque gazette contient des dizaines de textes différents — il faut les isoler pour le découpage et la recherche.  
**Résultat :** 126 textes FR (43 numérotés), 57 textes AR (31 numérotés). Textes clés retrouvés : loi 91-29, ordonnance 97-02/03/04, décret législatif 94-03.  
**Où :** `data/processed/texts/`, `data/processed/texts_ar/` (gitignored — régénérables).  
**Branches :** `feat/fr-pipeline` (PR #15), `feat/ar-pipeline` (PR #16) → fusionnées.

### 3.5 Extraction PDF texte (`src/collect/extract_text_pdfs.py`)

**Quoi :** extraction directe du texte des 18 PDF numériques (2005–2022) via `pymupdf.get_text()`.  
**Pourquoi :** ces PDF ont du texte intégré — pas besoin d'OCR ni de nettoyage.  
**Statut :** script prêt sur `main` (`3ff61d5`), **non encore exécuté**.  
**Où :** sortie vers `data/raw/joradp/text_v2/`, puis extraction directe.

### 3.6 Découpage loi 90-11 (`src/structure/split_loi_90_11.py`)

**Quoi :** découpage du texte de la loi 90-11 en 178 articles individuels.  
**Pourquoi :** le système RAG cherche par article, pas par page entière.  
**Comment :** reconnaissance des patterns `Art. N. —`, plus longue suite croissante, exclusion des faux titres, correction OCR (73 + 15 règles).  
**Résultat :** 172 articles loi 90-11 + 6 articles Constitution, 9/9 tests passent.  
**Limite :** source = WIPO Lex (temporaire), pas la sortie OCR JORADP. Script spécifique à la loi 90-11, pas généralisé.  
**Où :** `data/processed/articles.json`.  
**Branche :** fusionnée (PR #11).

## 4. Plan de corpus (Hadil BOUKHALFA)

**Quoi :** identification et indexation des 12 textes juridiques liés au droit du travail.  
**Pourquoi :** définir le périmètre exact du corpus (quel texte modifie quelles articles de la loi 90-11).  
**Résultat :** `corpus_index.csv` (12 entrées : 7 lois, 4 ordonnances, 1 décret législatif), plan documenté, échantillon d'évaluation.  
**Où :** `data/corpus_index.csv`, `docs/week2/corpus_plan.md`, `eval/relevance_sample.csv`.  
**Branche :** fusionnée (PR #17).

## 5. Évaluation LLM sans RAG (Rania Halima BENZERAFA)

**Quoi :** test du modèle (gpt-oss-120b via Groq) sur 16 questions de droit du travail, sans contexte RAG.  
**Pourquoi :** établir le baseline — mesurer les erreurs du LLM seul pour comparer après ajout du RAG.  
**Résultat :** Q1–Q10 (FR), Q11–Q16 (AR + cross-domain). Analyse des hallucinations (articles inventés, confusions entre lois). Notebook d'expérimentation.  
**Où :** `docs/week1/evaluation/` (3 fichiers).  
**Branches :** fusionnées (PR #24, #25, #26).  
**Limite :** pas de cache, pas de table d'erreurs structurée, pas de Hit@3.

## 6. Contributions

| Membre | Rôle | Livrable principal | Statut |
|--------|------|-------------------|--------|
| Nouha HAROUDI | Collecte, OCR, nettoyage, extraction FR/AR, rapport | `src/collect/`, `src/structure/`, rapports | Fusionné |
| Hadil BOUKHALFA | Plan de corpus, index, échantillon | `corpus_index.csv`, `corpus_plan.md` | Fusionné |
| Malak ALIOUAT | Découpage loi 90-11, corrections OCR | `split_loi_90_11.py`, `ocr_fix_map.csv` | Fusionné |
| Rania Halima BENZERAFA | Questions 11–16, analyse hallucinations | `docs/week1/evaluation/` | Fusionné |
| Malak BOUGOFFA | Retirée du groupe (18/11/2026) | — | Retrait confirmé par l'enseignant |

## 7. Limites

1. **9 gazettes exploitées sur 18** — les 9 scannées (1988–1997) sont traitées ; les 9 numériques (2005–2022) ont le script prêt mais non exécuté.
2. **Découpage limité à 90-11** — le script ne traite que la loi 90-11 (source WIPO), pas les 183 autres textes extraits.
3. **Pas de recherche sémantique** — BM25, embeddings (E5) et FAISS ne sont pas commencés.
4. **Pas de cache LLM** — les appels Groq ne sont pas mis en cache, pas de table d'erreurs par question.
5. **CER arabe non reproductible** — 0,0250 (13/520 caractères), échantillon trop petit, non utilisé comme preuve.

## 8. Calendrier

La plateforme place la recherche sémantique en semaine 2. Notre choix : la semaine 1 étant partielle, la semaine 2 complète la collecte, l'OCR et l'extraction ; la recherche sémantique passe en semaine 3.

## 9. Usage de l'IA

Scripts écrits avec un agent de code (Claude Code), relus et testés par l'équipe. Décisions juridiques et chiffres vérifiés manuellement.

## 10. Prochaines étapes (semaine 3)

| Qui | Quoi |
|-----|------|
| Nouha HAROUDI | Exécuter `extract_text_pdfs.py` (PDF 2005–2022), re-extraction FR/AR, fusion finale |
| Malak ALIOUAT | Généraliser le découpage à tous les textes, chunking pour embeddings, BM25 vs E5 |
| Hadil BOUKHALFA | Vérification corpus après fusion, embeddings |
| Rania Halima BENZERAFA | Cache LLM, table d'erreurs structurée, 5+ questions arabes obligatoires |
