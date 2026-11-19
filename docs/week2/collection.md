# Collecte automatisée — détails et preuves

**Branche :** `feat/collect-hardening` (`2231cad`), non fusionnée.
**Code :** `src/collect/download.py`, `src/collect/export_manifest.py`, `src/collect/select_issues.py`, `src/collect/inspect_pdfs.py`.
**Données :** `data/processed/issues_selected.csv`, `pdf_report.csv`, `downloads_manifest.csv`, `data/raw/joradp/index/`.

## 1. Politique d'accès

- `https://www.joradp.dz/robots.txt` → **HTTP 404** (2026-11-16). RFC 9309 : un 4xx vaut absence de restriction ; un 5xx aurait valu interdiction. Preuve : `docs/week2/robots_404_2026-11-16.png` (branche `docs/week2`, non fusionnée).
- L'index UpGrowth (CC BY 4.0) sert uniquement à lister les numéros et les URL officielles. Il n'est ni une source officielle ni un corpus. Ses limites sont décrites dans `sources_et_conditions.md` §4.
- Le site du ministère du Commerce (accès automatisé interdit) n'a pas été exploré.
- Client : `User-Agent` nommant le projet et un contact optionnel (`CONTACT_EMAIL`, par défaut l'URL du dépôt) ; délai minimum **3 s** entre requêtes ; **aucun** téléchargement parallèle ; volume limité aux numéros nécessaires.

## 2. Robustesse (une seule fois, ici)

- 3 tentatives par fichier, attente croissante (3 s puis 6 s) ; délais séparés connexion/lecture `(10, 300)`.
- `Retry-After` respecté sur HTTP 429 ; aucune nouvelle tentative sur un 4xx définitif.
- Taille maximale **50 Mo** : `stream=True`, `save_stream()` interrompt au-delà de la limite et supprime le `.part` ; un `Content-Length` annoncé trop grand est refusé avant téléchargement (journalisé, sans retry).
- Écriture atomique : `.part` → `fsync` → `os.replace`. Le SHA-256 est calculé **pendant** l'écriture et enregistré seulement après succès : un fichier présent est complet par construction.
- Journal d'échecs : `data/processed/download_failures.log` (ignoré par Git, absent sur le corpus actuel).
- Incident connu : un `ReadTimeout` sur `ar 2005/001` a interrompu une exécution **avant** l'ajout du `try/except` ; aucun fichier corrompu. Incident non journalisé (aucune trace écrite à l'époque) ; aucun fichier corrompu dans le corpus, et la relance après correction s'est terminée sans échec.

## 3. Registre et manifeste

- Registre local : `data/raw/joradp/downloads.sqlite` (**non versionné** : `*.sqlite` est ignoré). Colonnes : `k, url, sha256, path, bytes, fetched_at, issue, edition`.
- Preuve portable : `data/processed/downloads_manifest.csv` (versionné sur la branche), 36 lignes, chemins **relatifs**.
- 5 PDF antérieurs au registre (68/1991 FR+AR, 1/1993 FR+AR, 2/1993 FR) ont été re-téléchargés le 18/11 : SHA-256 **identiques** au serveur, puis enregistrés. 12 PDF ajoutés le 19/11 (6 numéros × FR/AR). Registre : 36/36.

## 4. Vérification exécutée le 19/11

```bash
.venv/bin/python src/collect/download.py | tail -1
# 0 fetched, 36 skipped, 0 failed
```

```bash
.venv/bin/python src/collect/verify_downloads.py
# 36/36 conformes | bad=[] | .part=0 | unregistered_pdf=0
```

Exécution du 18/11, conservée dans l'historique Git : `0 fetched, 24 skipped` et `24/24 conformes`. Aucun `.part` ; aucun PDF hors registre.

### 4.1 Preuves archivées

Les sorties réelles sont versionnées :

- `docs/week2/evidence/verify_downloads_2026-11-19.txt` — sortie de `src/collect/verify_downloads.py` (36/36 conformes, 0 `.part`, 0 PDF hors registre), avec en-tête date UTC + `git rev-parse --short HEAD`.
- `docs/week2/evidence/download_rerun_2026-11-19.txt` — exécution consécutive de `src/collect/download.py` : `0 fetched, 36 skipped, 0 failed`, code de sortie `0`.

Ces deux fichiers peuvent être régénérés par le professeur sans accès à la machine : le premier vérifie les fichiers réellement présents, le second prouve l'absence de doublon.

## 5. Périmètre réel

| Élément | Valeur |
|---|---|
| Numéros sélectionnés | 18 (10 planifiés + 8 échantillon) |
| PDF téléchargés | 36 (18 numéros × FR/AR) |
| PDF « scan » (OCR nécessaire) | 10 (5 numéros) |
| PDF « texte » non convertis | 26 (13 numéros, dont 2015/40 et les 6 numéros ajoutés le 19/11) |

Détail par fichier : `data/processed/pdf_report.csv` (36 lignes : langue, année, pages, caractères, `text`/`scan`).

## 6. Limites

- Les 13 numéros « texte » ne sont pas encore extraits : la couverture du corpus reste partielle (les nouveaux PDF sont présents, pas leurs textes).
- Le registre SQLite étant local, la preuve publiée est le manifeste CSV ; le manifeste ne contient pas les pages ni le type (`pdf_report.csv` le fait).
- `select_issues.py` combine une liste `KNOWN` (4 numéros) et `FROM_CORPUS_PLAN` (6 numéros / 7 textes identifiés dans PR #17, non fusionnée) ; `data/corpus_index.csv` est lu en complément s'il est présent. Ces 6 numéros sont collectés le 19/11 (PDF texte), extraction à faire.
- La sélection d'évaluation (2 numéros par année 1993/2005/2010/2020) est un **échantillon de commodité** figé le 16/11/2026, pas un tirage aléatoire : toute modification invaliderait le corpus déjà océrisé.
