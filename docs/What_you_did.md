# Team Contributions & Weekly Log

**Purpose:** This file tracks exactly what each member does every week.
**Rule:** Every member is responsible for writing their own contribution. Be specific (e.g., "Wrote the Python script to collect PDFs" instead of "Helped with collection"). Do not leave your line empty.

---

## Week 1 (13/11/2026) - Setup, Corpus & LLM Baseline
**Focus:** GitHub setup, Law 90-11 collection, Splitting script, Mission & Test Cases, LLM Baseline.

- **Nouha HAROUDI:** Created the GitHub organization and repository. Configured `.gitignore` and `requirements.txt`. Developed `test.py` to test the Groq API keys for the team. Helped clean the text data and found a text truncation bug in the splitting script.
- **Hadil BOUKHALFA:**
- **Rania Halima BENZERAFA:**
- **Malak BOUGOFFA:**
- **Malak ALIOUAT:**

---

## Week 2 (20/11/2026) - Semantic Search & Corpus Extension
**Focus:** Fix OCR errors, Collect amending texts, Test 10 questions on LLM, BM25 vs Embeddings.

- **Nouha HAROUDI:** Built the automated collection pipeline (download.py, inspect_pdfs.py, verify_downloads.py) — 36 PDFs collected (18 scanned + 18 digital). Built column-aware OCR v2 (ocr_columns.py) — 529 pages processed. Wrote cleaning scripts (clean_text.py, clean_ar.py) and extraction scripts (extract_texts.py, extract_texts_ar.py) — 126 FR texts + 57 AR texts extracted. Wrote extract_text_pdfs.py for digital PDFs. Built BM25 vs E5 search comparison pipeline (build_index.py, search_compare.py) — Hit@3: E5 69%, BM25 75% on 16 questions. Managed branch merges, .gitignore cleanup, and weekly reports.
- **Hadil BOUKHALFA:** Completed and corrected the corpus plan, source register, corpus index, and relevance sample, including legal-text metadata, relationships, and target articles. Checked source links, verified legal-text details. Added rapport_hadil.
- **Rania Halima BENZERAFA:** Added 10 new questions to reach 16 total (4 independent FR, 4 AR from Hadil's corpus, 2 hors-contexte). Added expected answers with sources/references in CSV format. Ran LLM without RAG (temperature=0, fixed seed) on all 16 questions. Analysed hallucinations: invented articles, law confusion, missing provisions. Documented in `docs/week1/evaluation/` (question-test.md, CSV, analysis MD, notebooks). Updated README.
- **Malak ALIOUAT:** Généralisation du découpage des textes juridiques en français et en arabe (split_articles.py) — 2 894 articles. Chunking (chunk_texts.py) — 2 903 chunks. Gestion des métadonnées et des identifiants uniques. Tests et vérification des résultats (test_split.py, ocr_fix_map.csv). Rapport : rapport_malak.md.

---

## Week 3 (27/11/2026) - Knowledge Graph & Versions
**Focus:** Define minimal ontology, extract entities and relations, track article versions.

- **Nouha HAROUDI:**
- **Hadil BOUKHALFA:** Implemented legal-relation extraction in `src/structure/extract_relations.py` and generated 297 candidate relations in `data/processed/relations.json`; evaluation against 104 mapped reference relations scored 96 predictions, with 96.9% precision and 89.4% recall. The scores apply only to relations covered by the reference set.
- **Rania Halima BENZERAFA:**
- **Malak ALIOUAT:**

---

## Week 4 (04/12/2026) - Reasoning & Rules
**Focus:** Write explicit rules, combine with LLM reasoning, practical case calculations.

- **Nouha HAROUDI:**
- **Hadil BOUKHALFA:**
- **Rania Halima BENZERAFA:**
- **Malak ALIOUAT:**

---

## Week 5 (11/12/2026) - Updates, Sources & Explainability
**Focus:** Handle versions/conflicts, show the trace, build the web interface (Streamlit).

- **Nouha HAROUDI:**
- **Hadil BOUKHALFA:**
- **Rania Halima BENZERAFA:**
- **Malak ALIOUAT:**

---

## Week 6 (18/12/2026) - Agent, Platform & Defense
**Focus:** Autonomous step chaining, final platform preparation, report, defense prep.

- **Nouha HAROUDI:**
- **Hadil BOUKHALFA:**
- **Rania Halima BENZERAFA:**
- **Malak ALIOUAT:**
