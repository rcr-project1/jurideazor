"""Offline tests for the collection scripts (no network)."""

from __future__ import annotations

import csv
import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collect import download  # noqa: E402
from collect.download import DownloadError, save_stream  # noqa: E402
from collect.select_issues import year_issue  # noqa: E402


def test_load_jobs_deduplicates_issues_and_languages(tmp_path: Path) -> None:
    index = tmp_path / "corpus_index.csv"
    rows = [
        {
            "text_id": "L-90-11",
            "jo_year": "1990",
            "jo_issue": "17",
            "url_fr": "https://www.joradp.dz/FTP/Jo-Francais/1990/F1990017.pdf",
            "url_ar": "https://www.joradp.dz/FTP/Jo-Arabe/1990/A1990017.pdf",
        },
        {
            "text_id": "L-90-03",
            "jo_year": "1990",
            "jo_issue": "6",
            "url_fr": "https://www.joradp.dz/FTP/Jo-Francais/1990/F1990006.pdf",
            "url_ar": "https://www.joradp.dz/FTP/Jo-Arabe/1990/A1990006.pdf",
        },
        {
            "text_id": "L-90-04",
            "jo_year": "1990",
            "jo_issue": "6",
            "url_fr": "https://www.joradp.dz/FTP/Jo-Francais/1990/F1990006.pdf",
            "url_ar": "https://www.joradp.dz/FTP/Jo-Arabe/1990/A1990006.pdf",
        },
        {
            "text_id": "O-97-02",
            "jo_year": "1997",
            "jo_issue": "3",
            "url_fr": "https://www.joradp.dz/FTP/Jo-Francais/1997/F1997003.pdf",
            "url_ar": "https://www.joradp.dz/FTP/jo-arabe/1997/A1997003.pdf",
        },
        {
            "text_id": "O-97-03",
            "jo_year": "1997",
            "jo_issue": "3",
            "url_fr": "https://www.joradp.dz/FTP/jo-francais/1997/F1997003.PDF",
            "url_ar": "https://www.joradp.dz/FTP/jo-arabe/1997/A1997003.pdf",
        },
    ]
    with index.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    assert download.load_jobs(index) == [
        (
            "fr",
            1990,
            6,
            "https://www.joradp.dz/FTP/Jo-Francais/1990/F1990006.pdf",
        ),
        (
            "ar",
            1990,
            6,
            "https://www.joradp.dz/FTP/Jo-Arabe/1990/A1990006.pdf",
        ),
        (
            "fr",
            1990,
            17,
            "https://www.joradp.dz/FTP/Jo-Francais/1990/F1990017.pdf",
        ),
        (
            "ar",
            1990,
            17,
            "https://www.joradp.dz/FTP/Jo-Arabe/1990/A1990017.pdf",
        ),
        (
            "fr",
            1997,
            3,
            "https://www.joradp.dz/FTP/Jo-Francais/1997/F1997003.pdf",
        ),
        (
            "ar",
            1997,
            3,
            "https://www.joradp.dz/FTP/jo-arabe/1997/A1997003.pdf",
        ),
    ]


def test_load_jobs_rejects_url_for_different_issue(tmp_path: Path) -> None:
    index = tmp_path / "corpus_index.csv"
    index.write_text(
        "jo_year,jo_issue,url_fr,url_ar\n"
        "1990,17,https://www.joradp.dz/FTP/jo-francais/1990/F1990006.pdf,\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match"):
        download.load_jobs(index)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.joradp.dz/FTP/Jo-Francais/1991/F1991068.pdf", (1991, 68)),
        ("https://www.joradp.dz/FTP/jo-francais/1994/F1994020.PDF", (1994, 20)),
        ("https://www.joradp.dz/FTP/JO-arabe/2022/A2022049.pdf?znjo=49", (2022, 49)),
        ("https://www.joradp.dz/Jo8499/1990/017/FP488.pdf", (1990, 17)),
    ],
)
def test_year_issue(url: str, expected: tuple[int, int]) -> None:
    assert year_issue(url) == expected


def test_year_issue_rejects_non_url() -> None:
    assert year_issue(None) is None
    assert year_issue("") is None


class FakeResponse:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks
        self.status_code = 200
        self.headers = {"Content-Length": str(sum(map(len, chunks)))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self) -> None:
        pass

    def iter_content(self, chunk_size: int):
        yield from self._chunks


def test_fetch_redownloads_invalid_registered_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "F1999999.pdf"
    payload = b"%PDF-1.4\n" + b"x" * 3000
    target.write_bytes(b"%PDF-1.4\n" + b"y" * 3000)
    monkeypatch.setattr(download, "dest", lambda *_args: target)
    monkeypatch.setattr(download.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(
        download.requests, "get", lambda *_args, **_kwargs: FakeResponse([payload])
    )

    con = sqlite3.connect(":memory:")
    con.execute(
        """CREATE TABLE downloads(
            k TEXT PRIMARY KEY, url TEXT, sha256 TEXT, path TEXT,
            bytes INTEGER, fetched_at TEXT, issue INTEGER, edition TEXT
        )"""
    )
    con.execute(
        "INSERT INTO downloads VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)",
        (
            "fr-1999-999",
            "https://example.test/current.pdf",
            hashlib.sha256(payload).hexdigest(),
            str(target),
            len(payload),
            999,
            "fr",
        ),
    )

    result = download.fetch(
        con, "fr", 1999, 999, "https://example.test/current.pdf"
    )

    assert result == "fetched"
    assert target.read_bytes() == payload
    record = con.execute(
        "SELECT url, sha256, bytes FROM downloads WHERE k=?",
        ("fr-1999-999",),
    ).fetchone()
    assert record == (
        "https://example.test/current.pdf",
        hashlib.sha256(payload).hexdigest(),
        len(payload),
    )
    assert (
        download.fetch(
            con, "fr", 1999, 999, "https://example.test/current.pdf"
        )
        == "skipped"
    )


def test_save_stream_rejects_html(tmp_path: Path) -> None:
    target = tmp_path / "F1999999.pdf"
    resp = FakeResponse([b"<html>error</html>" * 400])
    with pytest.raises(DownloadError):
        save_stream(resp, target)
    assert not target.exists()
    assert not list(tmp_path.glob("*.part"))


def test_save_stream_accepts_pdf(tmp_path: Path) -> None:
    target = tmp_path / "F1999999.pdf"
    payload = b"%PDF-1.4\n" + b"x" * 3000
    digest, size = save_stream(FakeResponse([payload]), target)
    assert target.exists()
    assert size == len(payload)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert not list(tmp_path.glob("*.part"))
