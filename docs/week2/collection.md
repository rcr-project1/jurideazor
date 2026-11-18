# Collecte automatisée — détails et preuves

**Branche :** `feat/collect-hardening` (`bdc2af9`), non fusionnée le 18/11/2026.
**Code :** `src/collect/download.py`, `src/collect/export_manifest.py`, `src/collect/select_issues.py`, `src/collect/inspect_pdfs.py`.
**Données :** `data/processed/issues_selected.csv`, `pdf_report.csv`, `downloads_manifest.csv`, `data/raw/joradp/index/`.

## 1. Politique d'accès

- `https://www.joradp.dz/robots.txt` → **HTTP 404** (2026-11-16). RFC 9309 : un 4xx vaut absence de restriction ; un 5xx aurait valu interdiction. Preuve : `docs/week2/robots_404_2026-11-16.png` (branche `docs/week2`, fusionnée par la PR de documentation).
- L'index UpGrowth (CC BY 4.0) sert uniquement à lister les numéros et les URL officielles. Il n'est ni une source officielle ni un corpus. Ses limites sont décrites dans `sources_et_conditions.md` §4.
- Le site du ministère du Commerce (accès automatisé interdit) n'a pas été exploré.
- Client : `User-Agent` identifiant avec adresse universitaire ; délai minimum **3 s** entre requêtes ; **aucun** téléchargement parallèle ; volume limité aux numéros nécessaires.

## 2. Robustesse (une seule fois, ici)

- 3 tentatives par fichier, attente croissante (3 s puis 6 s) ; délais séparés connexion/lecture `(10, 300)`.
- `Retry-After` respecté sur HTTP 429 ; aucune nouvelle tentative sur un 4xx définitif.
- Taille maximale **50 Mo** : `stream=True`, `save_stream()` interrompt au-delà de la limite et supprime le `.part` ; un `Content-Length` annoncé trop grand est refusé avant téléchargement (journalisé, sans retry).
- Écriture atomique : `.part` → `fsync` → `os.replace`. Le SHA-256 est calculé **pendant** l'écriture et enregistré seulement après succès : un fichier présent est complet par construction.
- Journal d'échecs : `data/processed/download_failures.log` (ignoré par Git, absent sur le corpus actuel).
- Incident connu : un `ReadTimeout` sur `ar 2005/001` a interrompu une exécution **avant** l'ajout du `try/except` ; aucun fichier corrompu. Incident non journalisé (aucune trace écrite à l'époque) ; aucun fichier corrompu dans le corpus, et la relance après correction s'est terminée sans échec.

## 3. Registre et manifeste

- Registre local : `data/raw/joradp/downloads.sqlite` (**non versionné** : `*.sqlite` est ignoré). Colonnes : `k, url, sha256, path, bytes, fetched_at, issue, edition`.
- Preuve portable : `data/processed/downloads_manifest.csv` (versionné sur la branche), 24 lignes, chemins **relatifs**.
- 5 PDF antérieurs au registre (68/1991 FR+AR, 1/1993 FR+AR, 2/1993 FR) ont été re-téléchargés le 18/11 : SHA-256 **identiques** au serveur, puis enregistrés. Registre : 24/24.

## 4. Vérification exécutée le 18/11

```bash
.venv/bin/python src/collect/download.py | tail -1
# 0 fetched, 24 skipped, 0 failed
```

```bash
.venv/bin/python - <<'PY'
import sqlite3, hashlib, pathlib
con = sqlite3.connect("data/raw/joradp/downloads.sqlite")
rows = con.execute("select k, path, sha256, bytes from downloads").fetchall()
ok = sum(1 for k, p, h, b in rows
         if pathlib.Path(p).exists()
         and hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() == h
         and pathlib.Path(p).stat().st_size == b
         and pathlib.Path(p).open("rb").read(5) == b"%PDF-")
print(f"{ok}/{len(rows)} conformes")
PY
# 24/24 conformes
```

Aucun `.part` ; aucun PDF hors registre.

### 4.1 Preuves archivées

Les sorties réelles sont versionnées :

- `docs/week2/evidence/verify_downloads_2026-11-18.txt` — sortie de `src/collect/verify_downloads.py` (24/24 conformes, 0 `.part`, 0 PDF hors registre), avec en-tête date UTC + `git rev-parse --short HEAD`.
- `docs/week2/evidence/download_rerun_2026-11-18.txt` — deux exécutions consécutives de `src/collect/download.py` : `0 fetched, 24 skipped, 0 failed`, code de sortie `0`.

Ces deux fichiers peuvent être régénérés par le professeur sans accès à la machine : le premier vérifie les fichiers réellement présents, le second prouve l'absence de doublon.

## 5. Périmètre réel

| Élément | Valeur |
|---|---|
| Numéros sélectionnés | 12 (4 modificatifs + 8 échantillon) |
| PDF téléchargés | 24 (12 numéros × FR/AR) |
| PDF « scan » (OCR nécessaire) | 10 (5 numéros) |
| PDF « texte » non convertis | 14 (7 numéros, dont 2015/40) |

Détail par fichier : `data/processed/pdf_report.csv` (24 lignes : langue, année, pages, caractères, `text`/`scan`).

## 6. Limites

- Les 7 numéros « texte » ne sont pas encore extraits : la couverture du corpus reste partielle.
- Le registre SQLite étant local, la preuve publiée est le manifeste CSV ; le manifeste ne contient pas les pages ni le type (`pdf_report.csv` le fait).
- `select_issues.py` combine une liste `KNOWN` (4 numéros) et `FROM_CORPUS_PLAN` (7 numéros identifiés dans PR #17, non fusionnée) ; `data/corpus_index.csv` est lu en complément s'il est présent. Les 7 numéros ne sont pas encore téléchargés.
- La sélection d'évaluation (2 numéros par année 1993/2005/2010/2020) est un **échantillon de commodité** figé le 16/11/2026, pas un tirage aléatoire : toute modification invaliderait le corpus déjà océrisé.
