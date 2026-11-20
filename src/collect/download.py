"""Download JORADP issues referenced by data/corpus_index.csv.

Writes one PDF per (language, year, issue) into data/raw/joradp/pdf/ and
registers URL, SHA-256 and byte size in data/raw/joradp/downloads.sqlite.
Multiple legal texts in the same Gazette issue share a single download.
Downloads are sequential, delayed, retried and size-limited; files are
written atomically and only registered after a %PDF- header check.

Usage:
    python src/collect/download.py
"""

from pathlib import Path
import csv
import hashlib
import os
import re
import sqlite3
import sys
import time
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
INDEX = ROOT / "data/corpus_index.csv"
RAW = ROOT / "data/raw/joradp"
DB = RAW / "downloads.sqlite"
CONTACT = os.environ.get("CONTACT_EMAIL", "https://github.com/rcr-project1/jurideazor")
UA = f"RCR-jurideazor (student project; contact: {CONTACT})"
DELAY = 3.0
ATTEMPTS = 3
TIMEOUT = (10, 300)
MAX_BYTES = 50 * 1024 * 1024
MIN_BYTES = 1000
FAIL_LOG = ROOT / "data/processed/download_failures.log"
INDEX_COLUMNS = {"jo_year", "jo_issue", "url_fr", "url_ar"}


def issue_from_url(url: str) -> tuple[int, int] | None:
    path = urlsplit(url).path
    match = re.search(r"/[FA](\d{4})(\d{3})\.pdf$", path, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.search(r"/(\d{4})/(\d{3})/[^/]+\.pdf$", path, re.IGNORECASE)
    return (int(match.group(1)), int(match.group(2))) if match else None


def url_identity(url: str) -> tuple[str, str, str]:
    parsed = urlsplit(url)
    return (
        parsed.scheme.casefold(),
        (parsed.hostname or "").casefold(),
        parsed.path.casefold(),
    )


def load_jobs(index: Path = INDEX) -> list[tuple[str, int, int, str]]:
    if not index.is_file():
        raise FileNotFoundError(
            f"corpus index not found: {index}\n"
            "Place the finalized corpus_index.csv at data/corpus_index.csv."
        )

    jobs: dict[tuple[str, int, int], str] = {}
    with index.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = set(reader.fieldnames or ())
        missing = INDEX_COLUMNS - columns
        if missing:
            raise ValueError(
                f"corpus index is missing required columns: {', '.join(sorted(missing))}"
            )

        for line, row in enumerate(reader, start=2):
            try:
                year = int(row["jo_year"])
                issue = int(row["jo_issue"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid jo_year or jo_issue on CSV line {line}"
                ) from exc
            if year < 1 or issue < 1:
                raise ValueError(f"invalid Gazette issue on CSV line {line}")

            found_language = False
            for lang, column in (("fr", "url_fr"), ("ar", "url_ar")):
                url = (row[column] or "").strip()
                if not url:
                    continue
                found_language = True
                parsed = urlsplit(url)
                if parsed.scheme != "https" or parsed.hostname not in {
                    "joradp.dz",
                    "www.joradp.dz",
                }:
                    raise ValueError(
                        f"expected an HTTPS JORADP URL in {column} on CSV line {line}"
                    )
                if issue_from_url(url) != (year, issue):
                    raise ValueError(
                        f"{column} URL does not match jo_year/jo_issue "
                        f"on CSV line {line}: {url}"
                    )

                key = (lang, year, issue)
                previous = jobs.get(key)
                if (
                    previous is not None
                    and url_identity(previous) != url_identity(url)
                ):
                    raise ValueError(
                        f"conflicting {lang} URLs for Gazette issue "
                        f"{year}/{issue:03d} on CSV line {line}"
                    )
                jobs.setdefault(key, url)
            if not found_language:
                raise ValueError(
                    f"no French or Arabic PDF URL on CSV line {line}"
                )

    if not jobs:
        raise ValueError(f"corpus index contains no downloadable issues: {index}")
    return [
        (lang, year, issue, url)
        for (lang, year, issue), url in sorted(
            jobs.items(),
            key=lambda item: (
                item[0][1],
                item[0][2],
                0 if item[0][0] == "fr" else 1,
            ),
        )
    ]

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

class DownloadError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_pdf_file(path: Path) -> tuple[str, int]:
    size = path.stat().st_size
    if size < MIN_BYTES:
        raise DownloadError(f"response too small ({size} bytes)")
    if size > MAX_BYTES:
        raise DownloadError(f"size exceeds {MAX_BYTES}-byte limit")
    with path.open("rb") as fh:
        head = fh.read(5)
    if head != b"%PDF-":
        raise DownloadError(f"not a PDF (starts with {head!r})")
    return sha256_file(path), size


def valid_registered_file(path: Path, digest: str, size: int) -> bool:
    if not path.is_file():
        return False
    try:
        actual_digest, actual_size = validate_pdf_file(path)
    except DownloadError:
        return False
    return actual_size == size and actual_digest == digest


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
        with tmp.open("rb") as fh:
            head = fh.read(5)
        if head != b"%PDF-":
            raise DownloadError(f"not a PDF (starts with {head!r})")
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


INSERT = (
    "INSERT OR REPLACE INTO downloads(k,url,sha256,path,bytes,fetched_at,issue,edition) "
    "VALUES (?,?,?,?,?,datetime('now'),?,?)"
)


def fetch(con, lang: str, year: int, issue: int, url: str) -> str:
    k = key(lang, year, issue)
    record = con.execute(
        "SELECT url, sha256, path, bytes FROM downloads WHERE k=?", (k,)
    ).fetchone()
    if record:
        record_url, digest, path, size = record
        registered_path = Path(path)
        if not registered_path.is_absolute():
            registered_path = ROOT / registered_path
        if record_url == url and valid_registered_file(
            registered_path, digest, size
        ):
            return "skipped"
        print(
            f"  WARN {k} -> registered file missing, changed or invalid; "
            "downloading again"
        )

    p = dest(lang, year, issue)
    if p.exists() and not record:
        try:
            digest, size = validate_pdf_file(p)
        except DownloadError as exc:
            log_failure(k, url, str(exc))
            print(f"  FAILED {k} -> {exc}")
            return "failed"
        con.execute(INSERT, (k, url, digest, str(p), size, issue, lang))
        con.commit()
        return "adopted"

    last = "unknown"
    for attempt in range(1, ATTEMPTS + 1):
        wait = DELAY * attempt
        try:
            with requests.get(
                url, headers={"User-Agent": UA}, timeout=TIMEOUT, stream=True
            ) as r:
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After", "")
                    wait = int(ra) if ra.isdigit() else DELAY * attempt
                    last = "HTTP 429"
                    print(f"  WARN tentative {attempt}/{ATTEMPTS} : HTTP 429, attente {wait}s")
                elif 400 <= r.status_code < 500:
                    reason = f"HTTP {r.status_code} (définitif, pas de nouvelle tentative)"
                    log_failure(k, url, reason)
                    print(f"  FAILED {k} -> {reason}")
                    return "failed"
                else:
                    r.raise_for_status()
                    announced = r.headers.get("Content-Length", "")
                    if announced.isdigit() and int(announced) > MAX_BYTES:
                        raise DownloadError(
                            f"taille annoncée {announced} > limite {MAX_BYTES}"
                        )
                    digest, size = save_stream(r, p)
                    con.execute(INSERT, (k, url, digest, str(p), size, issue, lang))
                    con.commit()
                    time.sleep(DELAY)
                    return "fetched"
        except DownloadError as exc:
            log_failure(k, url, str(exc))
            print(f"  FAILED {k} -> {exc} (voir download_failures.log)")
            time.sleep(DELAY)
            return "failed"
        except requests.RequestException as exc:
            last = type(exc).__name__
            print(f"  WARN tentative {attempt}/{ATTEMPTS} : {last}, attente {wait}s")
        if attempt < ATTEMPTS:
            time.sleep(wait)
    reason = f"{ATTEMPTS} tentatives épuisées (dernière : {last})"
    log_failure(k, url, reason)
    print(f"  FAILED {k} -> {reason}")
    time.sleep(DELAY)
    return "failed"


def main() -> int:
    try:
        jobs = load_jobs()
    except (FileNotFoundError, ValueError, csv.Error) as exc:
        print(f"cannot load corpus index: {exc}", file=sys.stderr)
        return 1

    con = init()
    counts = {"fetched": 0, "skipped": 0, "adopted": 0, "failed": 0}
    try:
        for lang, year, issue, url in jobs:
            res = fetch(con, lang, year, issue, url)
            counts[res] = counts.get(res, 0) + 1
            print(f"{res:8} {lang} {year}/{issue:03d}")
    finally:
        con.close()

    print(
        f"\n{counts['fetched']} fetched, {counts['skipped']} skipped, "
        f"{counts['adopted']} adopted, {counts['failed']} failed"
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())