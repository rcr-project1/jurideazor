# Rapport — Semaine 2 : collecte automatisée du Journal officiel

**Statut :** en cours (sections 4 remplie ; 5–7 à compléter)
**Dépôt :** `rcr-project1/jurideazor`
**Date :** 2026-11-17

## 1. Objectif de la semaine

Mettre en place la **collecte automatisée** des textes du Journal officiel algérien (JORADP), mesurer la qualité des fichiers obtenus, et préparer le découpage en textes puis le filtrage « droit du travail ». La recherche sémantique (BM25 / E5) vient ensuite, sur un corpus propre.

## 2. Sources et conditions d'utilisation

Détail complet : [`docs/week2/sources_et_conditions.md`](sources_et_conditions.md).

- `https://www.joradp.dz/robots.txt` → **HTTP 404** (2026-11-16). Selon la RFC 9309, un 4xx signifie qu'aucune restriction n'est déclarée ; un 5xx aurait été interprété comme une interdiction totale. Capture conservée dans `docs/week2/`.
- Site du **ministère du Commerce** : accès automatisé interdit → **non exploré**.
- Liste des numéros et URL : index ouvert **UpGrowth** (CC BY 4.0), utilisé uniquement comme index. Empreintes enregistrées :
  - `journal-officiel-archive.csv` — 752 103 B — `5732e90e…5fc063ae`
  - `jo-ref-index.json` — 860 626 B — `f90b6d28…308c17f94`
- **Loi 90-11** : texte de départ = **WIPO Lex** (version consolidée 1997), source **temporaire** (miroir non officiel) ; la source officielle finale reste la JORADP (numéro du 21 avril 1990). Provenance : `data/raw/PROVENANCE.md` ; PDF : `data/processed/downloads_manifest.csv` (URL + SHA-256).
- Collecte polie : `User-Agent` identifié (adresse universitaire), délai ≥ 3 s, aucun téléchargement parallèle, volume limité aux numéros nécessaires.

## 3. Collecte

| Élément | Valeur |
|---|---|
| Numéros sélectionnés (`issues_selected.csv`) | **12** (4 numéros portant des textes modificatifs + 8 pour l'échantillon) |
| PDF téléchargés | **24** (12 numéros × éditions FR et AR) |
| Registre `data/raw/joradp/downloads.sqlite` | **24 lignes** (url, sha256, taille, date, numéro, édition) |
| Fichiers antérieurs au registre | **5** (`1991/68` FR+AR, `1993/1` FR+AR, `1993/2` FR) → empreinte à compléter |

- **Non-duplication :** les exécutions suivantes n'ont rien retéléchargé ; toutes les lignes ressortent en `skipped` (registre + existence du fichier).
- **Incident connu :** un `ReadTimeout` sur `ar 2005/001` a interrompu une exécution **avant l'ajout du `try/except`**. Aucun fichier corrompu : l'écriture n'a lieu qu'après réception complète. Robustesse implémentée : 3 tentatives avec attente croissante, délais séparés connexion/lecture `(10, 300)`, écriture atomique `.part` → `fsync` → `os.replace`, empreinte SHA-256 du fichier, journal d'échecs `download_failures.log`.
- **Détail par fichier :** `data/processed/pdf_report.csv` (24 lignes : langue, année, fichier, pages, caractères, `text`/`scan`).

- **Robustesse du téléchargement :** 3 tentatives par fichier avec attente croissante (3 s, 6 s), délais séparés connexion/lecture `(10, 300)`, aucune nouvelle tentative sur les erreurs 4xx définitives, `Retry-After` respecté pour les 429.
- **Intégrité :** écriture atomique (`X.pdf.part` → `fsync` → `os.replace`), empreinte SHA-256 calculée **sur le fichier** et enregistrée après succès seulement. Un fichier présent est donc complet par construction.
- **Bornage et métadonnées :** taille maximale de 50 Mo (téléchargement interrompu au-delà, `.part` supprimé) ; le registre porte désormais `issue` et `edition` en colonnes explicites (24/24 lignes avec `issue`/`edition`).
- **Journal d'échecs :** `data/processed/download_failures.log` (vide sur le corpus actuel).
- **Vérification :** `0 fetched, 24 skipped, 0 failed` ; **24/24** empreintes vérifiées (SHA-256 + taille + en-tête `%PDF-`), 0 anomalie, 0 fichier `.part`.
## 4. Qualité de l'OCR

### 4.1 Périmètre

Tous les numéros antérieurs à 2002 sont des **images scannées** (0 caractère extractible). OCR appliqué uniquement à ces fichiers (`src/collect/ocr.py`), avec Tesseract (`fra`, `ara`), 300 dpi.

| Éditions scannées | Numéros | Pages | Résultat |
|---|---|---|---|
| FR + AR | 1991/068, 1993/001, 1993/002, 1994/020, 1997/003 | **258** | 10 fichiers, **aucun échec** |

Registre : `data/processed/ocr_report.csv` (pages, caractères, statut, durée). Sorties : `data/raw/joradp/text/<lang>/<année>/*.txt`. Le nombre de pages de chaque fichier texte **égale** celui du PDF correspondant.

### 4.2 Contrôle manuel sur 3 pages (comparaison avec l'image)

| # | Fichier / page | Vérifié | Résultat |
|---|---|---|---|
| 1 | `F1991068` p.7 | `Loi 91-29`, `Art. 73`, `73-1` à `73-6`, dates | ✅ numéros d'articles et dates corrects ; ❌ `53 → 58`, `66-156 → g6-136` (références du préambule) |
| 2 | `F1997003` p.6 | `Ordonnance 97-03`, `articles 22 à 26 et 157 alinéa 2`, `52 bis/ter/quater` | ✅ contenu juridique correct ; ❌ `1990 → 1996` (**une seule** occurrence, l. 323 ; ses deux jumelles l. 169 et 394 sont correctes), `11 → IT`, `Vu Ja loi`, `Article ler`, `travaiHeurs` |
| 3 | `F1991068` p.19 | deux tableaux (prix minima, semences) | ✅ tous les montants corrects ; ❌ `Article 1er → 17`, `786,50 → 78650`, `1299,20 → 129920`, `999 ‰ → 999 %`, colonne `R2 à R3` détachée |

**Conclusion mesurée :** les **numéros d'articles et les montants du corps des textes sont fiables** ; les **dates de référence et les décimales ne le sont pas** et doivent être vérifiées à la source. Aucun `Art. 73` erroné détecté.

### 4.3 Défaut structurel identifié

Les pages sont imprimées en **deux colonnes** ; l'OCR (`--psm 4`, page entière) lisait ligne par ligne sur toute la largeur et **entrelaçait** les deux colonnes : chaque ligne contenait la fin de la colonne gauche et le début de la colonne droite. Le texte n'était donc **pas découpable en l'état**.

### 4.4 Correction appliquée (v2)

`src/collect/ocr_columns.py` — aucune modification des fichiers v1, sortie dans `text_v2/` :

- **Français :** segmentation normale (`--psm 3`), puis reconstruction de l'ordre de lecture à partir des coordonnées : titre pleine largeur → colonne gauche → colonne droite → pied de page.
- **Arabe :** détection du blanc « gouttière » puis `--psm 4` sur chaque moitié d'image (colonne de droite d'abord), l'arabe donnant 226 mots contre 266 avec cette méthode sur une page témoin de 270 mots visibles.
- Détection de la gouttière limitée au corps de page (20–85 % de la hauteur) pour ignorer les bandeaux pleine largeur.

| Mesure | v1 (`text/`) | v2 (`text_v2/`) |
|---|---|---|
| Fichiers traités | 10 | **10** |
| Pages | 258 | **258** |
| Caractères | 671 391 | 656 444 (**0.978**) |
| Pages reconnues sur deux colonnes | — | **191 / 258** |
| Débuts d'article en début de ligne | 560 | **844 (+51 %)** |
| Durée | — | 24,3 min |

Le gain utile n'est pas le volume de caractères (v1 en produisait davantage en recopiant le texte à travers la gouttière) mais le nombre de **débuts d'articles détectables**, condition du découpage. Les fichiers v1 et v2 sont conservés ; la promotion (`text_v2` → `text`) reste à faire après validation par l'équipe.

Limites qui subsistent : dates de référence et décimales non fiables (vérification à la source), tableaux non exploitables (numéros d'articles agricoles hors périmètre), erreurs de caractères en arabe (`الثاتجة`, `المائدة`).

### 4.5 Langue arabe : mesure et décision

Un extrait de la page 6 de `A1997003` (articles 14 à 17 + clôture) a été saisi manuellement comme référence, puis comparé au texte OCR aligné sur le même intervalle (`src/eval/cer.py`, distance de Levenshtein après normalisation : diacritiques, tatweel, chiffres arabo-indiens → ASCII).

| Mesure | Résultat |
|---|---|
| CER (caractères) | **0,0250** (13 erreurs / 520 caractères) |
| Substitutions / suppressions / insertions | 6 / 4 / 3 |
| Chiffres faux | **1 / 19 (5,3 %)** |
| Années (4 chiffres) exactes | **2 / 2** |

Contrôle structurel complémentaire (`src/eval/digit_check.py`, comparaison des nombres à 4 chiffres entre les éditions FR et AR des 5 mêmes numéros) : sur 910 nombres arabes, 122 (13,4 %) sont absents de l'édition française, mais **tous les cas inspectés sont des numéros d'articles ou des montants** (`2585`, `2638`, `2438`, `2011`), pas des dates. Aucun `3000` dans l'ensemble du corpus arabe ; les 59 occurrences de `1996` dans `A1997003` sont des décrets légitimement datés de décembre 1996.

**Décision :** pas de ré-océrisation (`tessdata_best`), pas de correction par LLM. Les dates et numéros cités dans une réponse arabe sont **recopiés depuis l'édition française** de la même disposition ; seules les dispositions utilisées par les 5 questions arabes sont corrigées manuellement à partir de l'image. Une carte de correction de caractères (`ديسمير`→`ديسمبر` 59×, `سئة`→`سنة` 52×) reste disponible mais **facultative** (gain cosmétique, aucun effet sur les chiffres).

#### 4.5.1 Nettoyage — `src/structure/clean_ar.py`

5 fichiers, 148 pages, **290 093 → 284 668 caractères (98,1 % conservé)**. Supprimés : en-têtes courants (40 en 1991), bandeaux (2–7), lignes de couverture (3–7), lignes de sommaire à points (6), lignes de ponctuation seules. Règles strictes : **jamais un chiffre supprimé** (les lignes de chiffres seuls sont conservées : 9–54 par fichier), **jamais de jointure de mots** (l'arabe se coupe par espaces).

Cas limite corrigé avant livraison : « toute ligne contenant `الجريدة الرسمية` dans les 3 premières lignes = en-tête » supprimait du texte réel (`… ينشر هذا القرار فى الجريدة الرسمية`, art. 5, `A1994020` p24). Garde ajoutée (pas de `المادة`/`ينشر`/`في الجريدة` + ligne ≤ 120 car.). Contrôle : nombre de `المادة` inchangé (84 → 84 ; les +2/+3 viennent de l'écrasement des espaces).

#### 4.5.2 Extraction — `src/structure/extract_texts_ar.py`

**67 textes** (39 numérotés, 28 nominations sans article écartées), 38 numéros lisibles, **111 blocs sommaire/annonces écartés**, 0 doublon. En-têtes tolérants aux diacritiques (`مؤرّخ`, `مؤدخ`, `موؤرخ`) et aux numéros coupés/renversés (`7 9- 02` → `97-02`). Aucun numéro corrigé : `num_raw` conservé, `num_ok` explicite, identifiant temporaire sinon (`decret-1991-p24-1`).

#### 4.5.3 Croisement AR/FR — 33 identifiants numérotés communs

| Mesure | Résultat |
|---|---|
| Longueur médiane AR/FR | **0,81** |
| Textes dans ±30 % | **21 / 33** |
| Rappel des marqueurs d'article (AR strict) | **64,1 %** (67,3 % large, +71 citations) |

Écarts expliqués par preuve : tables budgétaires présentes seulement en FR (`decret-91-509`), contamination AR (`decret-94-76`, `decret-1997-p18-1`), contamination FR (`decret-93-05` : `Art. 6` deux fois, l.67 et l.394). Les écarts de dénombrement sont eux aussi expliqués : `loi-91-27/31`, `decret-93-06` et **`ordonnance-97-02`** existent en AR mais n'ont pas été extraits en FR ; `decret-91-514/518/521` et `decret-94-77` ont des numéros illisibles en AR.

Ancrage juridique vérifié en arabe : art. 2 = « **أربعين (40) ساعة** », art. 8 = « المواد من 22 إلى 26 من القانون رقم 11-90 » (le `157 al. 2` figure dans les visas FR et AR, pas dans l'art. 8). Point à vérifier sur l'image : l'art. 9 AR affiche `(2) اعتبارا من تاريخ نشره` sans « après deux (2) mois », et le marqueur `المادة 9` est perdu.

#### 4.5.4 Décision finale

Indexation des articles : **FR uniquement** (71 textes, marqueurs `Art. N`). L'arabe (67 textes) sert à la **vérification croisée** des nombres/dates et, plus tard, à une recherche plein texte ; aucune correction automatique de chiffre, les 5 questions arabes se corrigent sur l'image du PDF.

---

## 5. Découpage en textes et filtrage — *à compléter*

- Méthode : repérage des en-têtes (`LOI`, `ORDONNANCE`, `DECRET`, `ARRETE`…) + sommaire ; découpage par colonne.
- Filtrage en trois étapes : mots-clés du titre → modèle pour les cas ambigus → mesure sur échantillon annoté.
- Dépendance : `data/corpus_index.csv` et `eval/relevance_sample.csv` (en cours, Hadil) ; les métriques **Precision / Recall** seront ajoutées ici.

## 6. Recherche (BM25 vs E5) — *à compléter*

- BM25 (baseline) et E5 (`intfloat/multilingual-e5-base`, FAISS) sur le même jeu de questions.
- Métrique : **Hit@3**, plus analyse de 5 erreurs.
- Tableau `Méthode | Hit@3` à insérer.

## 7. Évaluation du LLM (sans RAG / avec sources) — *à compléter*

- Cache SQLite des appels Groq (`src/llm/cached_llm.py`), compteur `real`/`cached`.
- 10 questions minimum (`eval/questions.csv`), dont 1 hors corpus et 2 datées.
- Tableau des erreurs (références inventées, textes incomplets, refus manquants).

## 8. Limites et risques

1. Tout numéro antérieur à 2002 exige un OCR ; les dates OCR ne sont pas fiables sans vérification.
2. L'index UpGrowth est figé au **numéro 57/2026** et n'est pas une source officielle.
3. 5 PDF ne sont pas encore enregistrés dans le registre (pas d'empreinte).
4. L'OCR v2 n'est pas encore promu en version de référence (`text_v2` → `text`).
5. Le corpus actuel reste la seule loi 90-11 (version consolidée 1997) tant que les textes modificatifs ne sont pas intégrés.

## 9. Artefacts et preuves

| Fichier | Contenu |
|---|---|
| `src/collect/select_issues.py` | génère `issues_selected.csv` |
| `src/collect/download.py` | téléchargement poli + registre |
| `src/collect/inspect_pdfs.py` | `pdf_report.csv` (text/scan) |
| `src/collect/ocr.py` | OCR des seuls scans + `ocr_report.csv` |
| `data/processed/issues_selected.csv` | numéros retenus et justification |
| `data/processed/pdf_report.csv` | 24 lignes : pages, caractères, type |
| `src/collect/ocr_columns.py` | OCR v2 : ordre de lecture par colonnes, AR/FR |
| `data/processed/ocr_report.csv` | 10 lignes : pages, caractères, statut (v1) |
| `data/processed/ocr_report_v2.csv` | idem pour v2 |
| `data/processed/ocr_pages_v2.csv` | 258 lignes : une par page (caractères, colonnes, lignes) |
| `data/processed/ocr_manifest_v2.csv` | SHA-256 de chaque fichier `.txt` |
| `docs/week2/sources_et_conditions.md` | robots, licences, empreintes, mesures de politesse |

## 10. Contributions

| Membre | Tâche | Fichiers | Commit |
|---|---|---|---|
| Nouha HAROUDI | collecte, robots, politique de sources | `src/collect/*`, `sources_et_conditions.md` | *à compléter* |
| Hadil BOUKHALFA | plan de corpus, index, échantillon | `corpus_index.csv`, `relevance_sample.csv` | *à compléter* |
| Malak ALIOUAT | correction découpage, OCR, baseline | `ocr.py`, `split_loi_90_11.py` | *à compléter* |
| Rania Halima BENZERAFA | cache LLM, questions, tableau d'erreurs | `cached_llm.py`, `questions.csv` | *à compléter* |

## 11. Usage de l'IA

Voir `AI_USAGE.md`. Les outils d'IA ont servi à la rédaction et à la vérification ; toute affirmation du présent rapport renvoie à un fichier ou un commit.

## 12. Prochaines étapes

1. ✅ *Fait le 18/11* — les 5 PDF antérieurs au registre (68/1991, 1/1993, 2/1993) ont été re-téléchargés : SHA-256 **identiques** au serveur, lignes ajoutées, registre **24/24**.
2. Promouvoir `text_v2` puis découper en textes et filtrer.
3. Intégrer `corpus_index.csv` (Hadil) et remplacer la liste provisoire des 12 numéros.
4. Baseline BM25 / E5 (Hit@3) et évaluation du LLM avec cache.
