"""Offline tests for the collection scripts (no network)."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from collect.download import DownloadError, save_stream  # noqa: E402
from collect.select_issues import year_issue  # noqa: E402


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

    def iter_content(self, chunk_size: int):
        yield from self._chunks


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
