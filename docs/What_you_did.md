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

- **Nouha HAROUDI:** 
- **Hadil BOUKHALFA:**I completed and corrected the corpus plan, source register, corpus index, and relevance sample, including the legal-text metadata, relationships, and target articles, and add a rapport_hadil
I checked the source links, verified the legal-text details.
- **Rania Halima BENZERAFA:**
- # Travail réalisé

### 1. Préparation des questions de test

Dans le fichier **`question-test.md`**, j'ai ajouté 10 nouvelles questions aux 6 questions initiales, afin d'obtenir un total de **16 questions de test**, réparties comme suit :

- 4 questions indépendantes du thème du droit du travail algérien.
- 4 questions en arabe élaborées à partir du corpus juridique préparé par Hadil.
- 2 questions portant sur un autre thème, hors du domaine du droit du travail, afin de tester les limites du modèle.

### 2. Réponses avec sources et références

Dans le fichier **« Réponses avec sources et références »**, j'ai ajouté les réponses correspondant aux 10 nouvelles questions.

Pour les 4 questions indépendantes du thème du droit du travail, j'ai renseigné les réponses attendues, les sources, les références juridiques ainsi que les statuts.

Pour les 4 questions en arabe, élaborées à partir du corpus juridique préparé par Hadil, j'ai également identifié les réponses correspondantes, les sources, les références et les statuts présents dans le corpus.

Enfin, pour les 2 questions hors contexte, j'ai renseigné les réponses, les sources, les références et les statuts afin de permettre la vérification des résultats.

J'ai également converti le fichier du format **TXT au format CSV** afin de faciliter son exploitation.

### 3. Expérimentation du LLM sans RAG

Dans le fichier **`expérimentation_LLM_sans_RAG(3).ipynb`**, j'ai élaboré un prompt destiné à interroger le LLM sans utiliser de système RAG.

J'ai ensuite généré les réponses aux 16 questions en utilisant une température égale à 0, un seed fixe et la fonction `generate()`. Cette configuration vise à assurer la reproductibilité de l'expérience et à permettre la comparaison des réponses dans les mêmes conditions.

### 4. Analyse des réponses du LLM sans RAG

Dans le fichier **`Analyse des réponses du LLM sans RAG.md`**, j'ai intégré les réponses générées par le LLM sans RAG et effectué une analyse des nouvelles questions ajoutées.

Pour chaque question analysée, j'ai présenté :
- La question posée.
- La réponse générée par le LLM sans RAG.
- L'article juridique cité par le LLM.
- Les erreurs constatées, le cas échéant.
- Le type d'erreur identifié.

Cette analyse permet d'évaluer la capacité du LLM à répondre aux questions juridiques sans accès au corpus documentaire, ainsi qu'à identifier les erreurs, les références juridiques incorrectes et les éventuelles hallucinations produites par le modèle.
### 5. Mise à jour de la documentation

Enfin, j'ai rectifié et mis à jour le fichier README.md afin de refléter les modifications apportées, les nouveaux fichiers ajoutés et les différentes étapes de l'expérimentation.
- **Malak BOUGOFFA:** 
- **Malak ALIOUAT:**

    **Contribution :**
    - **Phase 0 :** Correction des erreurs de découpage des articles, amélioration du nettoyage OCR, ajout de tests et vérification des métadonnées (`version`, `date_debut`).
    - **Splitting :** Généralisation du découpage des textes juridiques en français et en arabe.
    - **Chunking :** Création des chunks à partir des articles et gestion des métadonnées.
    - **Améliorations techniques :** Gestion des identifiants uniques des chunks et vérification des résultats.
    
    **Fichiers principaux :**
    - `src/structure/split_articles.py`
    - `src/structure/chunk_texts.py`
    - `tests/test_split.py`
    - `src/structure/ocr_fix_map.csv`
    - `docs/week2/rapport_malak.md`

---

## Week 3 (27/11/2026) - Knowledge Graph & Versions
**Focus:** Define minimal ontology, extract entities and relations, track article versions.

- **Nouha HAROUDI:** 
- **Hadil BOUKHALFA:** 
- **Rania Halima BENZERAFA:** 
- **Malak BOUGOFFA:** 
- **Malak ALIOUAT:** 

---

## Week 4 (04/12/2026) - Reasoning & Rules
**Focus:** Write explicit rules, combine with LLM reasoning, practical case calculations.

- **Nouha HAROUDI:** 
- **Hadil BOUKHALFA:** 
- **Rania Halima BENZERAFA:** 
- **Malak BOUGOFFA:** 
- **Malak ALIOUAT:** 

---

## Week 5 (11/12/2026) - Updates, Sources & Explainability
**Focus:** Handle versions/conflicts, show the trace, build the web interface (Streamlit).

- **Nouha HAROUDI:** 
- **Hadil BOUKHALFA:** 
- **Rania Halima BENZERAFA:** 
- **Malak BOUGOFFA:** 
- **Malak ALIOUAT:** 

---

## Week 6 (18/12/2026) - Agent, Platform & Defense
**Focus:** Autonomous step chaining, final platform preparation, report, defense prep.

- **Nouha HAROUDI:** 
- **Hadil BOUKHALFA:** 
- **Rania Halima BENZERAFA:** 
- **Malak BOUGOFFA:** 
- **Malak ALIOUAT:**
- 
## Contribution de Benezerafa Rania Halima

Merci pour votre retour et vos remarques.

Concernant la contribution de Benezerafa Rania Halima, elle a créé et travaillé sur les fichiers suivants dans le dépôt GitHub :

- `fixermission.md`
- `question-test.md`
- `gitkeep.ipynb`
- `réponse avec sources et références`
- `analyse des réponses d’un LLM sans RAG`
- `réponses de LLM sans RAG`

Concernant l'évaluation du LLM sans RAG, elle a réalisé un premier cas pratique composé de six questions portant sur différentes situations liées au droit du travail algérien.

Pour chaque question, elle a analysé les réponses générées par le modèle en les comparant aux textes juridiques de référence. Elle a notamment identifié plusieurs types d'erreurs : des références juridiques inventées ou incorrectes, des confusions avec la législation française, des omissions de dispositions pertinentes, des erreurs d'interprétation, ainsi que des délais et des procédures non fondés.

Elle a également rédigé une analyse critique détaillant ces erreurs, leur gravité et leurs conséquences potentielles pour l'utilisateur, ainsi qu'une explication technique des hallucinations en l'absence de RAG.

Les réponses originales générées par le LLM sont conservées dans le fichier :'réponses de LLM sans RAG' ainsi que dans le notebook' gitkeep.ipynb', permettant de consulter et de vérifier les résultats obtenus.

Nous comprenons cependant que six questions ne constituent pas un échantillon suffisant pour démontrer ces limites de manière convaincante.

Nous allons donc compléter notre travail en ajoutant quatre questions indépendantes supplémentaires, afin d'atteindre un total de dix questions.

Pour chacune d'elles, nous présenterons clairement :

- La réponse réellement générée par le LLM ;
- Les articles juridiques cités par le modèle ;
- La vérification de ces références à partir des textes juridiques officiels ;
- Les erreurs identifiées (article inventé, mauvais numéro, omission ou mauvaise interprétation).

Nous allons également améliorer la présentation des résultats afin de fournir des preuves concrètes et une évaluation plus complète et rigoureuse du LLM sans RAG.

Merci pour vos orientations et vos remarques, qui nous permettront d'améliorer notre travail. 
--- 
