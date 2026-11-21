"""Build E5 and BM25 indices from chunks.json.

Computes multilingual embeddings (intfloat/multilingual-e5-base) on CPU,
stores them in FAISS IndexFlatIP. Also builds a BM25 index from the same
chunks. Both indices are saved to data/search/.

Run from the repository root:
    python src/search/build_index.py
    python src/search/build_index.py --batch-size 16   # lower if OOM
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.json"
OUT_DIR = ROOT / "data" / "search"

E5_MODEL = "intfloat/multilingual-e5-base"
FAISS_INDEX = "faiss_e5.index"
FAISS_IDS = "faiss_ids.json"
BM25_FILE = "bm25.json"
EMBEDDINGS_FILE = "embeddings.npy"


def load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"{CHUNKS_PATH} not found — run split_articles.py then chunk_texts.py first."
        )
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def build_e5_index(
    chunks: list[dict], batch_size: int = 32
) -> tuple[faiss.IndexFlatIP, np.ndarray]:
    print(f"Loading model: {E5_MODEL}")
    model = SentenceTransformer(E5_MODEL)

    texts = [f"passage: {c['content']}" for c in chunks]

    print(f"Encoding {len(texts)} chunks (batch_size={batch_size}, CPU)...")
    t0 = time.time()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    elapsed = time.time() - t0
    print(f"Encoding done: {elapsed:.1f}s ({len(texts)/elapsed:.1f} chunks/s)")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    print(f"FAISS index: {index.ntotal} vectors, dim={dim}")
    return index, embeddings


def tokenize(text: str) -> list[str]:
    import re
    return re.findall(r"\w+(?:'\w+)?", text.lower())


def build_bm25_index(chunks: list[dict]) -> tuple[BM25Okapi, list[list[str]]]:
    print("Building BM25 index...")
    tokenized = [tokenize(c["content"]) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    print(f"BM25 index: {len(tokenized)} documents")
    return bm25, tokenized


def main() -> None:
    parser = argparse.ArgumentParser(description="Build E5 + BM25 search indices")
    parser.add_argument("--batch-size", type=int, default=32, help="E5 encoding batch size")
    parser.add_argument("--skip-e5", action="store_true", help="skip E5/FAISS, build BM25 only")
    args = parser.parse_args()

    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ids = [c["chunk_id"] for c in chunks]
    (OUT_DIR / FAISS_IDS).write_text(
        json.dumps(ids, ensure_ascii=False), encoding="utf-8"
    )

    if not args.skip_e5:
        index, embeddings = build_e5_index(chunks, batch_size=args.batch_size)
        faiss.write_index(index, str(OUT_DIR / FAISS_INDEX))
        np.save(str(OUT_DIR / EMBEDDINGS_FILE), embeddings)
        print(f"Saved: {OUT_DIR / FAISS_INDEX}")
        print(f"Saved: {OUT_DIR / EMBEDDINGS_FILE}")

    _, tokenized = build_bm25_index(chunks)
    (OUT_DIR / BM25_FILE).write_text(
        json.dumps({"tokenized": tokenized}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved: {OUT_DIR / BM25_FILE}")

    print("\nDone. Run search_compare.py to query both indices.")


if __name__ == "__main__":
    main()
