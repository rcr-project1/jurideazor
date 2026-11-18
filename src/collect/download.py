from pathlib import Path
import hashlib, os, sqlite3, time

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "data/processed/issues_selected.csv"
RAW = ROOT / "data/raw/joradp"
DB = RAW / "downloads.sqlite"
UA = "RCR-jurideazor (student project; contact: nouha.haroudi@univ-constantine2.dz)"
DELAY = 3.0
ATTEMPTS = 3
TIMEOUT = (10, 300)
MAX_BYTES = 50 * 1024 * 1024
MIN_BYTES = 1000
FAIL_LOG = ROOT / "data/processed/download_failures.log"

def key(lang: str, year: int, issue: int) -> str:
    return f"{lang}-{year}-{issue:03d}"

def dest(lang: str, year: int, issue: int) -> Path:
    return RAW / "pdf" / lang / str(year) / f"{'F' if lang == 'fr' else 'A'}{year}{issue:03d}.pdf"

def init() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS downloads(
        k TEXT PRIMARY KEY, url TEXT, sha256 TEXT, path TEXT,
        bytes INTEGER, fetched_at TEXT, issue INTEGER, edition TEXT)""")
    cols = {row[1] for row in con.execute("PRAGMA table_info(downloads)")}
    for name, kind in (("issue", "INTEGER"), ("edition", "TEXT")):
        if name not in cols:
            con.execute(f"ALTER TABLE downloads ADD COLUMN {name} {kind}")
    for (k,) in con.execute(
        "SELECT k FROM downloads WHERE issue IS NULL OR edition IS NULL"
    ).fetchall():
        parts = k.split("-")
        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            con.execute(
                "UPDATE downloads SET issue=?, edition=? WHERE k=?",
                (int(parts[2]), parts[0], k),
            )
    con.commit()
    return con

def get_with_retries(url: str):
    for attempt in range(1, ATTEMPTS + 1):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, stream=True)
            r.raise_for_status()
            return r
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 429:
                ra = exc.response.headers.get("Retry-After", "")
                wait = int(ra) if ra.isdigit() else DELAY * attempt
            elif 400 <= status < 500:
                print(f"  ERROR HTTP {status} (définitif, pas de nouvelle tentative)")
                return None
            else:
                wait = DELAY * attempt
            print(f"  WARN tentative {attempt}/{ATTEMPTS} : HTTP {status}, attente {wait}s")
        except requests.RequestException as exc:
            wait = DELAY * attempt
            print(f"  WARN tentative {attempt}/{ATTEMPTS} : {type(exc).__name__}, attente {wait}s")
        if attempt < ATTEMPTS:
            time.sleep(wait)
    print(f"  ERROR {ATTEMPTS} tentatives épuisées")
    return None

class DownloadError(Exception):
    pass


def save_stream(resp, p: Path, max_bytes: int = MAX_BYTES) -> tuple[str, int]:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    h = hashlib.sha256()
    size = 0
    try:
        with tmp.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_bytes:
                    raise DownloadError(
                        f"taille > {max_bytes} octets (limite), téléchargement interrompu"
                    )
                h.update(chunk)
                fh.write(chunk)
            fh.flush()
            os.fsync(fh.fileno())
        if size < MIN_BYTES:
            raise DownloadError(f"réponse trop petite ({size} octets)")
        os.replace(tmp, p)
        return h.hexdigest(), size
    finally:
        tmp.unlink(missing_ok=True)


def log_failure(k: str, url: str, reason: str) -> None:
    FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
    header = not FAIL_LOG.exists()
    with FAIL_LOG.open("a", encoding="utf-8") as fh:
        if header:
            fh.write("# horodatage\tcle\turl\traison\n")
        fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{k}\t{url}\t{reason}\n")

def fetch(con, lang: str, year: int, issue: int, url: str) -> str:
    k = key(lang, year, issue)
    if con.execute("SELECT 1 FROM downloads WHERE k=?", (k,)).fetchone():
        return "skipped"
    p = dest(lang, year, issue)
    if p.exists():
        return "skipped"
    try:
        r = get_with_retries(url)
        if r is None:
            raise DownloadError("réseau : tentatives épuisées")
        announced = r.headers.get("Content-Length", "")
        if announced.isdigit() and int(announced) > MAX_BYTES:
            r.close()
            raise DownloadError(f"taille annoncée {announced} > limite {MAX_BYTES}")
        try:
            digest, size = save_stream(r, p)
        finally:
            r.close()
    except (DownloadError, OSError) as exc:
        log_failure(k, url, str(exc))
        print(f"  FAILED {k} -> {exc} (voir download_failures.log)")
        time.sleep(DELAY)
        return "failed"
    con.execute("INSERT INTO downloads VALUES (?,?,?,?,?,datetime('now'),?,?)",
                (k, url, digest, str(p), size, issue, lang))
    con.commit()
    time.sleep(DELAY)
    return "fetched"

def main() -> None:
    sel = pd.read_csv(INDEX)
    con = init()
    counts = {"fetched": 0, "skipped": 0, "failed": 0}
    for row in sel.itertuples():
        jobs = []
        if row.edition_fr == 1 and isinstance(row.url_fr, str):
            jobs.append(("fr", row.url_fr))
        if row.edition_ar == 1 and isinstance(row.url_ar, str):
            jobs.append(("ar", row.url_ar))
        for lang, url in jobs:
            res = fetch(con, lang, row.year, row.issue, url)
            counts[res] = counts.get(res, 0) + 1
            print(f"{res:8} {lang} {row.year}/{row.issue:03d}")
    print(f"\n{counts['fetched']} fetched, {counts['skipped']} skipped, {counts['failed']} failed")
if __name__ == "__main__":
    main()