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

- **Nouha HAROUDI:** Fixed Arabic digit reversal in extract_text_pdfs.py (18 AR files re-extracted). Fixed diacritics regex in extract_texts_ar.py (+3 AR texts). Built link_ar_to_fr.py for AR↔FR linking by gazette position. Implemented hybrid search RRF in search_compare.py with auto-alpha (FR=0.7, AR=0.8) calibrated by sweep. Added alef normalization (query-time only; corpus normalization caused E5 regression). Extended test set from 16 to 30 questions. Corrected ground truth for 20/30 questions. Fixed shadda regex in split_articles.py (+178 AR articles, 3238→3410 chunks). Added article-level Hit@3 and MRR scoring to search_compare.py. Injected metadata prefix [loi-XX-YY] into BM25 and E5 chunks in build_index.py — Hybrid law-level 96%, article-level 77%. Built Kaggle E5 notebook (kaggle_build_e5.py). Defined Knowledge Graph ontology (527 nodes, 787 edges, 6 relation types) in docs/week3/ontology.md. Built GraphRAG prototype comparison (graph_rag_compare.py) — tested 5 questions, GraphRAG improves 3/5 including Q24 corrected from 44h to 40h using article_versions.json. Wrote rapport semaine 3.
- **Hadil BOUKHALFA:** Implemented legal-relation extraction in `src/structure/extract_relations.py` and generated 297 candidate relations in `data/processed/relations.json`; evaluation against 104 mapped reference relations scored 96 predictions, with 96.9% precision and 89.4% recall. The scores apply only to relations covered by the reference set.
- **Rania Halima BENZERAFA:** Fixed question 12. Evaluated OCR quality on 5 scanned pages of Law 90-11 (JORADP No. 17, pp. 490–494; 3,231 words) against a manual reference transcription, Results: WER 1.05%, CER 0.46%, Documented OCR errors and evaluation results. Created data/processed/article_versions.json to track the version history of 73 articles of Law 90-11 (129 dated versions), identifying which articles were original, added, modified, supplemented, or repealed, Each version includes its date, source text, and summaries in French and Arabic.
- **Malak ALIOUAT:** Wrote `src/structure/build_graph.py`, which builds the knowledge graph with NetworkX (12 Law, 629 Article, 129 Version nodes; 6 relation types) and saves it as GraphML (770 nodes, 899 edges). Merged FR/AR texts into one node per article (law_id + article number), expanded grouped references ("140 et 149", "22 à 26"), cleaned illegal XML characters (`\x0c`) so the file opens correctly, and resolved 31 MODIFIES/COMPLETES conflicts (version history wins). Added 10 validation rules (all pass). Applied review fixes (ROOT paths, `build_graph()` with `__main__` guard). Documented known issues (no Arabic text for 88-07, 15-01 and 94-03; 9 articles without text). Wrote `rapport_malak.md` for week 3.

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
