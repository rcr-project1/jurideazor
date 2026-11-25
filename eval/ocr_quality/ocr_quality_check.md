# OCR quality check — JORADP
## Méthodologie

- Échantillon : 5 pages du JORADP n° 17 du 25 avril 1990 (pp. 490-494, loi 90-11), scannées.
- Référence (gold) : transcription manuelle faite à partir de l'image du PDF, telle qu'imprimée
  (fautes d'origine conservées : « colatéral », « pélérinage », « degrès »).
- Ordre de lecture : colonne gauche puis colonne droite ; en-têtes et numéros de page
  retirés par le script avant la comparaison (présents dans les fichiers).
- OCR comparé : data/raw/joradp/text_v2/.
- Normalisation (identique des deux côtés) : apostrophes et tirets unifiés, mots coupés en fin
  de ligne recollés, espaces normalisées.
- Métriques : WER, CER, chiffres faux (dates, montants, pourcentages, nombres) et numéros
  d'articles faux.

- Textes complets (gold et OCR) : eval/ocr_quality/gold/loi_90_11_p490.txt à p494.txt
  (transcription) et eval/ocr_quality/ocr_pages/loi_90_11_p490.txt à p494.txt (OCR text_v2).



Gold = transcription manuelle ; tokens = mots `[\w']+` après normalisation ; erreurs = S+D+I (difflib).

| Fichier | Page | Mots gold | Mots faux | WER | CER | Chiffres faux | N° d'articles faux |
|---|---|---|---|---|---|---|---|
| loi_90_11 | 490 | 684 | 2 | 0.29% | 0.35% | 0/26 | 0/15 |
| loi_90_11 | 491 | 667 | 9 | 1.35% | 0.95% | 1/27 | 1/17 |
| loi_90_11 | 492 | 629 | 6 | 0.95% | 0.31% | 0/16 | 0/14 |
| loi_90_11 | 493 | 593 | 12 | 2.02% | 0.43% | 0/15 | 0/11 |
| loi_90_11 | 494 | 658 | 5 | 0.76% | 0.27% | 1/16 | 0/11 |
| **TOTAL** | | 3231 | 34 | **1.05%** | **0.46%** | **2/100** | **1/68** |



## loi_90_11 — page 490
**Erreurs mots** (contexte | gold → OCR)
- `par l'une ou` | **l'autre** → **d'autre** (replace)
- `pénibles dangereux ou` | **impliquant** → **impliquent** (replace)

**Erreurs numériques** : aucune

**Mots à scripts mélangés (homoglyphes)** : aucun


## loi_90_11 — page 491
**Erreurs mots** (contexte | gold → OCR)
- `` | **∅** → **En Cr er RQ COS ES** (insert)
- `3 Travail posté` | **Art** → **Ârt** (replace)
- `roulement les structures` | **et** → **et'** (replace)
- `qui s'étend du` | **1er** → **1** (replace)

**Erreurs numériques** : 1er→1

**Mots à scripts mélangés (homoglyphes)** : aucun


## loi_90_11 — page 492
**Erreurs mots** (contexte | gold → OCR)
- `la détermination de` | **la** → **Ja** (replace)
- `spéciales payées ou` | **autorisées** → **auto risées** (replace)
- `Art 51 Le` | **programme** → **programmé** (replace)
- `de départ en` | **congé** → **eongé** (replace)
- `autorisations d'absences spéciales` | **non** → **nor** (replace)

**Erreurs numériques** : aucune

**Mots à scripts mélangés (homoglyphes)** : aucun


## loi_90_11 — page 493
**Erreurs mots** (contexte | gold → OCR)
- `l'employeur Section 2` | **De la** → **Dela** (replace)
- `des périodes de` | **maintien** → **maiñtien** (replace)
- `droit de grève` | **∅** → **_** (insert)
- `par l'effet de` | **la** → **ja** (replace)
- `à durée déterminée` | **la** → **ja** (replace)
- `avec l'organisme employeur` | **présente** → **pré sente** (replace)
- `à une compression` | **d'effectifs** → **'d'effectifs** (replace)
- `travail à de` | **nouveaux** → **nouveaüx** (replace)
- `nouveaux recrutements dans` | **les catégories** → **les_catégories** (replace)

**Erreurs numériques** : aucune

**Mots à scripts mélangés (homoglyphes)** : aucun


## loi_90_11 — page 494
**Erreurs mots** (contexte | gold → OCR)
- `` | **∅** → **RS** (insert)
- `est calculé sur` | **la** → **l4** (replace)
- `résulte de la` | **classification** → **classifica 'tion** (replace)
- `de nuit et` | **l'indemnité** → **indemnité** (replace)

**Erreurs numériques** : ∅→l4

**Mots à scripts mélangés (homoglyphes)** : aucun



## Conclusion

Sur 5 pages du JORADP n° 17 du 25 avril 1990 (pp. 490-494, loi 90-11), soit 3 231 mots,
le taux d'erreur est de **1,05 % (WER)** et **0,46 % (CER)**. En retirant 7 tokens de
bruit d'en-tête, le WER est d'environ 0,84 %.

- Chiffres : 1 seule erreur numérique réelle (« 1er » lu « 1 », art. 40) ; aucun
  montant ni pourcentage faux (20 %, 50 %, 2000, 44 conservés).
    (Le tableau compte 2 : le second est « l4 » pour « la », art. 72, une lettre
  lue comme chiffre.)
- Numéros d'articles : 1/68 non reconnu (art. 30) : la balise est lue « Ârt. 30 » ;
  le numéro 30 lui-même est correct. Une coupe par expression régulière sur
  « Art. » manquerait cet article.
- Types d'erreurs dominants : substitutions de lettres (l→j, a→4), mots coupés
  en fin de ligne non recollés, espaces perdues ou ajoutées.

Limites : échantillon de 5 pages d'un seul numéro ; la comparaison est faite après
normalisation (coupures de mots recollées, en-têtes retirés), et un tiret de mot
composé supprimé par l'OCR ne serait pas détecté.
