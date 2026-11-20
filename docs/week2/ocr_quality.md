# Qualité de l'OCR et des textes — détails et preuves

**Branches :** `feat/ocr-v2` (`673701b`), `feat/fr-pipeline` (`94864fc`), `feat/ar-pipeline` (`b00fb37`). Non fusionnées le 19/11/2026.
**Code :** `src/collect/ocr_columns.py`, `src/eval/cer.py`, `src/eval/digit_check.py`, `src/structure/clean_text.py`, `extract_texts.py`, `clean_ar.py`, `extract_texts_ar.py`.

## 1. Périmètre OCR

Tous les numéros antérieurs à 2002 sont des images (0 caractère extractible). OCR appliqué à ces 10 fichiers seulement (5 numéros × FR/AR), Tesseract `fra`/`ara`, 300 dpi.

| Éditions | Numéros | Pages | Résultat |
|---|---|---|---|
| FR + AR | 1991/068, 1993/001, 1993/002, 1994/020, 1997/003 | **258** | 10 fichiers, aucun échec |

Registre : `data/processed/ocr_report_v2.csv` (10 lignes : pages, caractères, statut, durée). Sorties : `data/raw/joradp/text_v2/` (10 fichiers `.txt`, un par PDF). Empreintes : `ocr_manifest_v2.csv` (SHA-256 par fichier `.txt`).

## 2. Défaut v1 et correction v2

Défaut : pages imprimées sur **deux colonnes** ; l'OCR v1 lisait la page entière ligne par ligne et **entrelaçait** les colonnes. Le texte n'était pas découpable.

Correction (`ocr_columns.py`) :
- français : segmentation normale puis reconstruction de l'ordre de lecture à partir des coordonnées (titre pleine largeur → colonne gauche → colonne droite → pied) ;
- arabe : détection du blanc de gouttière, puis OCR de chaque moitié d'image, colonne de droite d'abord ;
- détection de la gouttière limitée au corps de page (20–85 % de la hauteur) pour ignorer les bandeaux.

| Mesure (v2) | Valeur |
|---|---|
| Fichiers / pages | 10 / **258** |
| Caractères produits | **656 444** |
| Pages reconnues sur deux colonnes (`cols = 2`) | **191 / 258** |
| Durée totale | 24,4 min |

Preuve : `data/processed/ocr_pages_v2.csv` (258 lignes, colonne `cols`).
Les chiffres de la v1 ne sont pas cités : le texte v1 n'est pas versionné (`data/raw/joradp/text/` est ignoré par Git).

## 3. Contrôle manuel sur 3 pages

Comparaison avec l'image du PDF, consignée dans la version 1 du rapport :

| # | Fichier / page | Vérifié | Résultat |
|---|---|---|---|
| 1 | `F1991068` p.7 | `Loi 91-29`, `Art. 73`, `73-1`…`73-6`, dates | numéros d'articles et dates corrects ; références du préambule fausses (`53 → 58`, `66-156 → g6-136`) |
| 2 | `F1997003` p.6 | `Ordonnance 97-03`, « articles 22 à 26 et 157 alinéa 2 », `52 bis/ter/quater` | contenu juridique correct ; `1990 → 1996` une fois (l. 323) ; `11 → IT`, `Article ler`, `travaiHeurs` |
| 3 | `F1991068` p.19 | deux tableaux (prix minima, semences) | montants du corps corrects ; `Article 1er → 17`, `786,50 → 78650`, `1299,20 → 129920`, `999 ‰ → 999 %`, colonne `R2 à R3` détachée |

**Conclusion exacte :** dans cet échantillon, les **numéros d'articles** sont corrects ; les **séparateurs décimaux**, certaines **dates de référence** et les **tableaux** ne le sont pas. Les montants corrects concernent le corps du tableau, pas les décimales.

## 4. Arabe : mesure et décision

- Référence saisie à la main : `src/eval/ar_truth/A1997003_p6.txt`, **520 caractères** (articles 14 à 17 + clôture).
- Mesure annoncée dans la version 1 : **CER = 0,0250** (13 erreurs / 520), 1 chiffre faux sur 19.
- **Cette mesure n'est pas reproductible** avec l'artefact actuel : `src/eval/cer.py` appliqué à `data/raw/joradp/text_v2/ar/1997/A1997003.txt` ne retrouve pas l'intervalle correspondant (le découpage en pages du fichier ne coïncide pas avec la page de la référence). Elle n'est **pas** utilisée comme preuve ; elle est à refaire avec un ancrage de début et de fin explicites.
- Contrôle structurel, lui reproductible (`src/eval/digit_check.py`, `data/processed/digit_check.csv`) : sur 5 numéros et **910** nombres arabes à 4 chiffres, **122 (13,4 %)** sont absents de l'édition française ; les cas inspectés sont surtout des numéros d'articles ou des montants, mais un cas est une **date fausse** (`1988` au lieu de `1989`, `F1997003`, ligne 6 de `digit_check.csv`). **La précision des chiffres et des dates en arabe n'est pas mesurée.**

**Décision :** pas de ré-océrisation, pas de correction par LLM. Les dates et numéros cités dans une réponse arabe sont recopiés depuis l'édition française ; les dispositions utilisées par les questions arabes seront corrigées à la main sur l'image.

## 5. Nettoyage et extraction

### 5.1 Français

| Mesure | Valeur |
|---|---|
| Fichiers / pages conservées | 5 / 110 |
| Caractères avant → après | 365 600 → 361 146 |
| Textes extraits (`kept`) | **71** (37 numérotés) |
| Blocs supprimés (sommaire + décrets de nomination sans article) | **126** |
| Caractères des textes retenus | 277 270 |

Preuves : `clean_report.csv`, `extract_report.csv`, `data/processed/texts/index.csv` (71 lignes + en-tête).

### 5.2 Arabe

| Mesure | Valeur |
|---|---|
| Fichiers / pages | 5 / 148 |
| Caractères avant → après | 290 093 → **284 668** (98,1 %) |
| Textes extraits | **67** (39 numérotés, 38 numéros lisibles) |
| Blocs supprimés (sommaire + décrets de nomination sans article) | **111** |
| Doublons | 0 |

Preuves : `clean_report_ar.csv`, `extract_report_ar.csv`, `data/processed/texts_ar/index_ar.csv` (67 lignes + en-tête).

Les nombres **126 / 111** sont des **chunks supprimés**, pas des textes juridiques : ils incluent le sommaire et les décrets de nomination sans article. Dans le numéro 1997/003, **19 décrets de nomination français et 12 arabes** sont de vrais décrets (sans article), comptés dans ces chunks.

Règles de nettoyage : aucun chiffre supprimé (les lignes de chiffres seuls sont conservées), aucune jointure de mots, en-têtes retirés seulement dans les 3 premières lignes et en l'absence de `المادة`/`ينشر`/`في الجريدة` (garde ajoutée après un cas limite : l'article 5 de `A1994020` p.24 contenait `ينشر هذا القرار فى الجريدة الرسمية`).
Règles d'extraction : en-têtes tolérants aux diacritiques (`مؤرّخ`, `مؤدخ`, `موؤخر`) et aux numéros coupés/renversés (`7 9- 02` → `97-02`) ; numéro jamais corrigé (`num_raw` conservé, `num_ok` explicite).

## 6. Croisement AR/FR

Sur les **33** identifiants numérotés présents dans les deux index : longueur médiane AR/FR = **0,814** ; **21 / 33** textes à ±30 %. Calcul reproductible depuis `data/processed/texts/index.csv` et `data/processed/texts_ar/index_ar.csv`.

Écarts identifiés : `ordonnance-97-02`, `loi-91-27`, `loi-91-31`, `decret-93-06` et `decret-91-510` existent en AR mais pas en extraction FR ; `decret-91-514/518/521` et `decret-94-77` ont des numéros illisibles en AR.

## 7. Limites

- Échantillon manuel : **3 pages** FR et **1 extrait de 520 caractères** en AR. Aucune généralisation n'est possible.
- La mesure CER arabe est à refaire (§4).
- Le fichier `decret-1997-p18-1` est contaminé (12 530 caractères) ; `decret-1997-p03-1` l'est aussi : il contient également le texte de l'ordonnance 97-01.
- L'ordonnance 97-02 n'est pas extraite comme texte indépendant : son texte FR est dans `decret-1997-p03-1` (contaminé), son texte AR dans `ordonnance-97-02`. L'ordonnance 97-01 n'est extraite dans aucune des deux langues.
- Les tableaux et les décimales restent non fiables : vérification à la source obligatoire.
