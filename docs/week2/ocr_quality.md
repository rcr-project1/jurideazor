# Qualité de l'OCR et des textes — détails et preuves

**Branches :** `feat/ocr-v2` (`590c503`), `feat/fr-pipeline` (`997db23`), `feat/ar-pipeline` (`eaa0b96`). Non fusionnées le 20/11/2026.
**Code :** `src/collect/ocr_columns.py`, `src/eval/cer.py`, `src/eval/digit_check.py`, `src/structure/clean_text.py`, `extract_texts.py`, `clean_ar.py`, `extract_texts_ar.py`.

## 1. Périmètre OCR

Tous les numéros antérieurs à 2002 sont des images (0 caractère extractible). OCR appliqué à **18 fichiers** (9 numéros × FR/AR), Tesseract `fra`/`ara`, 300 dpi.

| Éditions | Numéros | Pages | Résultat |
|---|---|---|---|
| FR + AR | 1988/004, 1990/006, 1990/017, 1991/068, 1993/001, 1993/002, 1994/020, 1996/043, 1997/003 | **529** | 18 fichiers, aucun échec, 0 page vide |

Registre : `data/processed/ocr_report_v2.csv` (18 lignes : pages, caractères, statut, durée). Sorties : `data/raw/joradp/text_v2/` (18 fichiers `.txt`, un par PDF). Empreintes : `ocr_manifest_v2.csv` (SHA-256 par fichier `.txt`).

## 2. Défaut v1 et correction v2

Défaut : pages imprimées sur **deux colonnes** ; l'OCR v1 lisait la page entière ligne par ligne et **entrelaçait** les colonnes. Le texte n'était pas découpable.

Correction (`ocr_columns.py`) :
- français : segmentation normale puis reconstruction de l'ordre de lecture à partir des coordonnées (titre pleine largeur → colonne gauche → colonne droite → pied) ;
- arabe : détection du blanc de gouttière, puis OCR de chaque moitié d'image avec padding 1 %, colonne de droite d'abord ;
- détection de la gouttière limitée au corps de page (20–85 % de la hauteur) pour ignorer les bandeaux ;
- correction 20/11 (`15ceed1`) : attribution des lignes par centre (`cx`) au lieu de marges chevauchantes — élimine les lignes dupliquées près de la gouttière.

| Mesure (v2) | Valeur |
|---|---|
| Fichiers / pages | 18 / **529** |
| Caractères produits | **~1 491 000** (FR ~849 000, AR ~643 000) |
| Pages vides | **0** |
| Pipes FR (F1991068) | 114 (v1 : 403) |
| Pipes AR (A1991068) | 151 |

Preuve : `data/processed/ocr_pages_v2.csv` (529 lignes, colonne `cols`).
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
| Fichiers nettoyés | 5 (texte v1 ; v2 en attente de merge) |
| Textes extraits (`kept`) | **126** (43 numérotés, 83 non numérotés) |
| Pipes dans les titres | **0** |
| Textes contaminés (colonnes entrelacées) | 52 (signalés, conservés) |

Corrections du 20/11 (`997db23`) : qualificatif `législatif` ajouté au BOUNDARY ; découpage des en-têtes mid-line (`MID_LINE_HEADING`) ; nettoyage des pipes dans `clean_title()` ; détection de contamination par pipes dans le corps (≥3 lignes).

Textes clés retrouvés : loi-91-29, ordonnance-97-02/03/04, décret-94-03.

Preuves : `extract_report.csv`, `data/processed/texts/index.csv` (126 lignes + en-tête).

### 5.2 Arabe

| Mesure | Valeur |
|---|---|
| Fichiers nettoyés | 5 (texte v1 ; v2 en attente de merge) |
| Textes extraits | **57** (31 numérotés) |
| Pipes dans les titres | **0** |
| Titres vides | **0** |

Corrections du 20/11 (`eaa0b96`) : qualificatifs `تشريعي` (législatif) et `عضوي` (organique) ajoutés ; `+` comme variante OCR du tiret ; `clean_title()` étendu à 4 lignes avec nettoyage pipes/accolades.

Textes clés retrouvés : ordonnance-97-02/03, décret-94-05. Manquants (OCR v1 trop garbled) : décret-94-03, loi-91-29 — à récupérer après merge du texte v2.

Preuves : `extract_report_ar.csv`, `data/processed/texts_ar/index_ar.csv` (57 lignes + en-tête).

Règles de nettoyage : aucun chiffre supprimé, aucune jointure de mots, en-têtes retirés avec garde (`المادة`/`ينشر`/`في الجريدة`).
Règles d'extraction : en-têtes tolérants aux diacritiques (`مؤرّخ`, `مؤدخ`, `موؤخر`) et aux numéros coupés/renversés (`7 9- 02` → `97-02`) ; numéro jamais corrigé (`num_raw` conservé, `num_ok` explicite).

## 6. Croisement AR/FR

Croisement à refaire après merge du texte v2 dans les deux pipelines. L'ordonnance 97-02, absente en FR dans la version précédente, est maintenant extraite dans les deux langues.

## 7. Limites

- Échantillon manuel : **3 pages** FR et **1 extrait de 520 caractères** en AR. Aucune généralisation n'est possible.
- La mesure CER arabe est à refaire (§4).
- 52 textes FR signalés comme contaminés (colonnes entrelacées dans le corps) — conservés mais à vérifier manuellement pour les textes clés.
- Décret 94-03 (AR) : heading OCR encore bruité (`مرسوم " تشزيعي`) — à récupérer après merge du texte v2.
- L'ordonnance 97-01 n'est extraite dans aucune des deux langues (heading mid-line non récupéré).
- Les 6 PDF « texte » (2015, 2017, 2022) nécessitent un extracteur `pymupdf.get_text()`, pas de Tesseract.
- Les tableaux et les décimales restent non fiables : vérification à la source obligatoire.
