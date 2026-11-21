import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "src" / "structure" / "chunk_texts.py"
spec = importlib.util.spec_from_file_location("chunk_texts", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_numbered_article_stays_one_chunk():
    records = [{"source_file": "texts/1990/loi-90-11.txt", "lang": "fr", "year": 1990,
                "text_type": "loi", "article": "1", "content": "mot " * 700}]
    chunks = module.make_chunks(records)
    assert len(chunks) == 1
    assert chunks[0]["article"] == "1"


def test_short_full_text_stays_one_chunk():
    records = [{"source_file": "texts/1996/decret.txt", "lang": "fr", "year": 1996,
                "text_type": "decret", "article": None, "content": "Petit texte juridique."}]
    chunks = module.make_chunks(records)
    assert len(chunks) == 1
    assert chunks[0]["article"] is None


def test_long_full_text_is_split_without_losing_words():
    content = (" ".join(f"mot{i}" for i in range(600)) + "\n\n" +
               " ".join(f"terme{i}" for i in range(300)))
    records = [{"source_file": "texts/1996/decret.txt", "lang": "fr", "year": 1996,
                "text_type": "decret", "article": None, "content": content}]
    chunks = module.make_chunks(records)
    assert len(chunks) >= 2
    assert sum(len(c["content"].split()) for c in chunks) == len(content.split())


def test_metadata_and_ids_are_present():
    records = [{"source_file": "texts_ar/1991/loi.txt", "lang": "ar", "year": 1991,
                "text_type": "loi", "article": "2", "content": "نص المادة"}]
    chunk = module.make_chunks(records)[0]
    for key in ("chunk_id", "source_file", "lang", "year", "text_type", "article", "content", "char_count"):
        assert key in chunk
    assert chunk["lang"] == "ar"
