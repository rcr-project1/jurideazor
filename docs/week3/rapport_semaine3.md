# Rapport de la semaine 3

**Date :** 22/11/2026. **Dépôt :** `rcr-project1/jurideazor`.

## 1. Résumé

| Fait | Chiffre |
|------|---------|
| Extraction AR corrigée (diacritiques) | 123 textes (68 numérotés, +3 vs semaine 2) |
| Liaison AR ↔ FR par position gazette | 5 textes liés, 17 déjà corrects |
| Chunks disponibles | 3 141 (vs 2 903 semaine 2) |
| Recherche hybride (RRF) | Implémentée, alpha configurable |
| Auto-alpha multilingue | FR α=0.7, AR α=0.3 + boost réf. croisé |
| Hit@3 BM25 | 13/16 (81 %) |
| Hit@3 E5 | 10/16 (62 %) |
| Hit@3 Hybrid | 12/16 (75 %) |
| MRR BM25 | 0.6875 |
| MRR E5 | 0.6562 |
| MRR Hybrid | 0.6406 |
| Index E5 (Colab GPU) | 3 141 vecteurs, 768 dim, ~31 s |


## 2. Corrections de la semaine 2

**Remarque du professeur (priorité haute) :** « Mesurer la recherche hybride au lieu de l'estimer. Le ~92 % annoncé est une projection, pas un résultat. Preuve attendue : le résultat de l'hybride mesuré avec le script commun, avec un tableau par question. »

| Remarque du prof | Action | Preuve | Statut |
|------------------|--------|--------|--------|
| ~92 % est une projection, pas un résultat | Hybrid mesuré avec `search_compare.py --auto-alpha` : **12/16 (75 %)** | Tableau par question §4, `data/search/comparison_results.json` | ✅ Fait |
| Q14 (loi 22-16) déclarée « absente » | La loi n'était pas absente : deux bugs pipeline — (1) regex `الماد[ةه]` ignorait la shadda `المادّة` → texte éliminé, (2) OCR inversait `22-16` → `22-61` → fichier mal nommé | `extract_report_ar.csv` : `loi-22-61,kept`, `index_ar.csv` : `link_fr=loi-22-16` | ✅ Fait |
| Q12 (question méta) non évaluable | Q12 passe avec auto-alpha : Hybrid=YES(r2) grâce à α=0.3 + boost références `91-29,90-11` | Tableau §4, ligne Q12 | ✅ Fait |
| Écart BM25/E5 = 1 question, pas concluant | Ajout du Hybrid comme 3e méthode + analyse par langue (FR vs AR) pour montrer les forces de chaque méthode | Analyse §4 | ✅ Fait |

## 3. Travail réalisé

### 3.1 Correction extraction arabe (`extract_texts_ar.py`)

**Problème :** le regex `الماد[ةه]` ne reconnaissait pas `المادّة` (avec shadda ّ), ce qui éliminait des textes contenant des articles.
**Cause :** le OCR arabe insère des diacritiques entre les lettres ; le regex ne les tolérait pas.
**Correction :** `ARTICLE = re.compile(rf"الماد{DIACRITICS}[ةه]")` — le même pattern de diacritiques déjà utilisé par `BOUNDARY`.
**Impact :** loi 22-16 arabe (4 762 caractères, 5 articles) n'est plus éliminée comme « table des matières ». +3 textes extraits pour la gazette 2022.
**Preuve :** `data/processed/extract_report_ar.csv` : `loi-22-61,kept,1,4762`.

### 3.2 Liaison arabe–français (`link_ar_to_fr.py`) — NOUVEAU

**Problème :** l'OCR arabe inverse les chiffres (RTL) : `22-16` → `22-61`, `22-15` → `22-51`.
**Solution :** les gazettes FR et AR sont des éditions miroir (même numéro, même ordre). Le script :
1. Regroupe les textes par numéro de gazette et par type (loi, décret, etc.)
2. Les trie par page d'apparition
3. Associe chaque texte AR à son homologue FR par position
4. Renomme le fichier AR avec l'identifiant FR correct
5. Corrige le numéro inversé dans l'en-tête du texte AR

**Résultat :**
- 5 textes liés par position (`loi-22-51→loi-22-15`, `loi-22-61→loi-22-16`, `loi-22-71→loi-22-17`, 2 ordonnances 1996)
- 17 textes déjà corrects (même identifiant FR et AR)
- 89 ignorés (nombre de textes différent entre FR et AR — les décrets/arrêtés non numérotés)
- `index_ar.csv` mis à jour : colonnes `link_fr`, `link_method`

**Où :** `src/structure/link_ar_to_fr.py`, `data/processed/texts_ar/index_ar.csv`.

### 3.3 Recherche hybride RRF (`search_compare.py`)

**Quoi :** fusion des résultats BM25 et E5 par Reciprocal Rank Fusion.
**Formule :** `score(d) = α/(K + rank_bm25 + 1) + (1−α)/(K + rank_e5 + 1)`, K=60.
**Référence :** Chapitre 3 Cours 1, diapositive 32.
**Où :** `src/search/search_compare.py`, fonction `search_hybrid()`.

### 3.4 Auto-alpha multilingue + boost références croisées

**Problème 1 (diapo 14, « problème de Sofiane ») :** BM25 score = 0 quand la question et le contenu sont en langues différentes. Pas de tokens communs entre arabe et français.
**Problème 2 (diapo 38) :** les embeddings ne garantissent pas la correspondance exacte des numéros de loi.

**Solution — deux mécanismes activés par `--auto-alpha` :**

1. **Auto-alpha par langue :** détection de la langue de la question (proportion de caractères arabes > 30 %). Questions arabes → α=0.3 (favorise E5 pour le cross-langue). Questions françaises → α=0.7 (favorise BM25 pour les mots-clés exacts).

2. **Boost références juridiques croisées :** extraction des numéros de loi de la question (regex `\d+-\d+`). Recherche BM25 séparée avec uniquement ces tokens (ex : `22-16`, `90-11`). Résultats fusionnés dans le score RRF avec poids 0.3. Ce boost trouve des chunks dans les deux langues via les numéros partagés.

**Résultat :** Q12 (AR, loi 91-29) passe de NO(r4) à YES(r2) grâce au boost. Q13 recule de YES(r1) à NO(r4) — compromis attendu du changement d'alpha.
**Où :** `src/search/search_compare.py`, fonctions `detect_lang()`, `extract_legal_refs()`, `search_bm25_refs()`.

### 3.5 Index E5 sur GPU (`build_e5_colab.ipynb`)

**Quoi :** notebook Colab pour encoder les 3 141 chunks sur GPU T4 au lieu du CPU local.
**Pourquoi :** l'encodage CPU prend ~30 min ; sur GPU T4, ~31 s (×60 plus rapide).
**Comment :** monte Google Drive, lit `chunks.json`, encode avec `intfloat/multilingual-e5-base`, sauvegarde `faiss_e5.index` + `embeddings.npy` + `faiss_ids.json`.
**Où :** `build_e5_colab.ipynb` (racine du dépôt).

## 4. Résultats de la comparaison (mesurés)

Tous les chiffres ci-dessous sont le résultat de l'exécution de `search_compare.py --auto-alpha --k 3` sur les 16 questions de `eval/test_questions.json`. Aucune estimation ni projection.

```
$ python src/search/search_compare.py --questions eval/test_questions.json --k 3 --auto-alpha

BM25 vs E5 vs Hybrid (auto-alpha) — Top-3 sur 16 questions

Q 1 [fr]  E5=YES(r1)  BM25=YES(r1)  Hybrid=YES(r2)  α=0.7
Q 2 [fr]  E5=YES(r1)  BM25=YES(r1)  Hybrid=YES(r1)  α=0.7
Q 3 [fr]  E5=YES(r1)  BM25=YES(r1)  Hybrid=YES(r1)  α=0.7
Q 4 [fr]  E5=YES(r1)  BM25=YES(r2)  Hybrid=YES(r2)  α=0.7
Q 5 [fr]  E5=YES(r1)  BM25=YES(r2)  Hybrid=YES(r2)  α=0.7
Q 6 [fr]  E5=YES(r1)  BM25=YES(r1)  Hybrid=YES(r1)  α=0.7
Q 7 [fr]  E5=YES(r1)  BM25=YES(r1)  Hybrid=YES(r1)  α=0.7
Q 8 [fr]  E5=YES(r1)  BM25=YES(r1)  Hybrid=YES(r1)  α=0.7
Q 9 [fr]  E5=YES(r1)  BM25=YES(r2)  Hybrid=YES(r1)  α=0.7
Q10 [fr]  E5=YES(r1)  BM25=YES(r1)  Hybrid=YES(r1)  α=0.7
Q11 [ar]  E5=NO (r4)  BM25=YES(r1)  Hybrid=YES(r1)  α=0.3
Q12 [ar]  E5=NO (r—)  BM25=YES(r2)  Hybrid=YES(r2)  α=0.3  refs=91-29,90-11
Q13 [ar]  E5=NO (r4)  BM25=YES(r1)  Hybrid=NO (r4)  α=0.3  refs=97-03,90-11
Q14 [ar]  E5=NO (r—)  BM25=NO (r—)  Hybrid=NO (r—)  α=0.3  refs=22-16,90-11
Q15 [fr]  E5=NO (r—)  BM25=NO (r—)  Hybrid=NO (r—)  α=0.7
Q16 [fr]  E5=NO (r—)  BM25=NO (r—)  Hybrid=NO (r—)  α=0.7

Hit@3 : E5 62 %, BM25 81 %, Hybrid 75 %
MRR   : E5 0.6562, BM25 0.6875, Hybrid 0.6406
```

**Analyse :**
- **Q1–Q10 (FR→FR) :** E5 parfait (10/10 au rang 1). BM25 et Hybrid aussi, grâce aux tokens exacts.
- **Q11–Q13 (AR→AR) :** BM25 domine (3/3). E5 échoue en top-3 car l'espace sémantique multilingue ne place pas les chunks arabes au rang 1 pour des requêtes très spécifiques.
- **Q14 (AR→FR, loi 22-16) :** triple échec. La loi 22-16 est **présente** dans le corpus (FR : 6 chunks, AR : 3 chunks). Le titre arabe est corrigé (`22-16`), mais le corps contient encore `09–11` (OCR inversé de `90-11`). BM25 ne peut pas faire de cross-langue (diapo 14). E5 ne garantit pas les numéros (diapo 38). Hybrid hérite des deux échecs (diapo 32 : « si les deux se trompent, l'hybride se trompe aussi »). **Ce n'est pas un problème d'absence mais de dégradation OCR des numéros référencés à l'intérieur du texte arabe.**
- **Q15, Q16 :** hors corpus — assurance automobile et code de la famille ne font pas partie du droit du travail.

## 5. Limites

1. **Q14 reste NO** — l'OCR arabe endommage les numéros de loi à l'intérieur du texte (pas seulement l'en-tête). La correction actuelle ne touche que le titre ; une correction complète du corps nécessiterait un alignement mot à mot FR↔AR.
2. **E5 faible sur l'arabe** — 0/4 questions arabes en top-3. Le modèle `multilingual-e5-base` sous-performe sur le vocabulaire juridique arabe spécialisé. BGE-M3 (1 024 dim) pourrait faire mieux mais n'a pas été testé.
3. **Alpha compromis** — Q12 s'améliore avec α=0.3 (AR), mais Q13 régresse. Un alpha adaptatif par question (pas seulement par langue) serait meilleur.
4. **Pas de RAG end-to-end** — la recherche est prête, mais la génération de réponse (LLM + contexte) n'est pas encore intégrée.

## 6. Contributions

| Membre | Rôle | Livrable principal | Statut |
|--------|------|-------------------|--------|
| Nouha HAROUDI | Correction extraction AR, liaison FR↔AR, recherche hybride, auto-alpha, rapport | `extract_texts_ar.py`, `link_ar_to_fr.py`, `search_compare.py`, `build_e5_colab.ipynb` | PR en cours |
| Hadil BOUKHALFA | Ajout du champ `within_scope` au corpus index (correction semaine 2) | `data/corpus_index.csv`, `docs/week2/corpus_plan.md` (commit `02ee03b`) | Fait |
| Malak ALIOUAT | — | — | — |
| Rania Halima BENZERAFA | — | — | — |

## 7. Pipeline complet (semaine 3)

```
PDF → OCR → clean_text.py / clean_ar.py
                ↓
        extract_texts.py / extract_texts_ar.py
                ↓
          link_ar_to_fr.py  ← NOUVEAU
                ↓
          split_articles.py → chunk_texts.py
                ↓
          build_index.py (BM25 + E5/FAISS)
                ↓
          search_compare.py --auto-alpha
```

## 8. Usage de l'IA

Scripts écrits avec un agent de code (opencode), relus et testés par l'équipe. Décisions juridiques et chiffres vérifiés manuellement. Encodage E5 exécuté sur Google Colab (GPU T4).
