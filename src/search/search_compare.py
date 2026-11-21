"""Compare BM25 vs E5 semantic search on test questions.

Loads both indices built by build_index.py, runs queries, prints side-by-side
top-k results, and computes Hit@k for each method.

Run from the repository root:
    python src/search/search_compare.py
    python src/search/search_compare.py --k 5
    python src/search/search_compare.py --questions path/to/questions.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CHUNKS_PATH = DATA / "processed" / "chunks.json"
SEARCH_DIR = DATA / "search"
RESULTS_PATH = SEARCH_DIR / "comparison_results.json"

E5_MODEL = "intfloat/multilingual-e5-base"

BUILTIN_QUESTIONS = [
    {
        "question": "Quelle est la durée légale du travail en Algérie ?",
        "lang": "fr",
        "expected_article": "Art. 22",
        "expected_law": "loi-90-11",
    },
    {
        "question": "Quels sont les droits du travailleur en cas de licenciement abusif ?",
        "lang": "fr",
        "expected_article": "Art. 73",
        "expected_law": "loi-90-11",
    },
    {
        "question": "Quelle est la durée de la période d'essai ?",
        "lang": "fr",
        "expected_article": "Art. 18",
        "expected_law": "loi-90-11",
    },
    {
        "question": "Comment se calcule l'indemnité de licenciement ?",
        "lang": "fr",
        "expected_article": "Art. 73-4",
        "expected_law": "loi-91-29",
    },
    {
        "question": "ما هي مدة العمل القانونية في الجزائر؟",
        "lang": "ar",
        "expected_article": "المادة 22",
        "expected_law": "loi-90-11",
    },
    {
        "question": "ما هي حقوق العامل في حالة التسريح التعسفي؟",
        "lang": "ar",
        "expected_article": "المادة 73",
        "expected_law": "loi-90-11",
    },
    {
        "question": "Quelles sont les conditions de la grève ?",
        "lang": "fr",
        "expected_article": "Art. 23",
        "expected_law": "loi-90-02",
    },
    {
        "question": "Quels sont les cas de suspension de la relation de travail ?",
        "lang": "fr",
        "expected_article": "Art. 64",
        "expected_law": "loi-90-11",
    },
]


def load_chunks() -> list[dict]:
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def load_e5_index() -> tuple[faiss.IndexFlatIP, SentenceTransformer]:
    index = faiss.read_index(str(SEARCH_DIR / "faiss_e5.index"))
    model = SentenceTransformer(E5_MODEL)
    return index, model


def load_bm25_index() -> BM25Okapi:
    data = json.loads((SEARCH_DIR / "bm25.json").read_text(encoding="utf-8"))
    return BM25Okapi(data["tokenized"])


def load_ids() -> list[str]:
    return json.loads((SEARCH_DIR / "faiss_ids.json").read_text(encoding="utf-8"))


def search_e5(
    query: str, model: SentenceTransformer, index: faiss.IndexFlatIP, k: int
) -> list[tuple[int, float]]:
    q_emb = model.encode(
        [f"query: {query}"], normalize_embeddings=True
    ).astype(np.float32)
    scores, indices = index.search(q_emb, k)
    return [(int(indices[0][i]), float(scores[0][i])) for i in range(k)]


def tokenize(text: str) -> list[str]:
    import re
    return re.findall(r"\w+(?:'\w+)?", text.lower())


def search_bm25(
    query: str, bm25: BM25Okapi, k: int
) -> list[tuple[int, float]]:
    tokens = tokenize(query)
    scores = bm25.get_scores(tokens)
    top_k = np.argsort(scores)[::-1][:k]
    return [(int(i), float(scores[i])) for i in top_k]


def check_hit(results: list[tuple[int, float]], chunks: list[dict], expected_law: str) -> bool:
    if not expected_law or expected_law.startswith("__"):
        return False
    laws = [l.strip() for l in expected_law.split(",")]
    for idx, _ in results:
        source = chunks[idx].get("source_file", "")
        if any(law in source for law in laws):
            return True
    return False


def run_comparison(questions: list[dict], k: int) -> dict:
    chunks = load_chunks()
    ids = load_ids()
    index, model = load_e5_index()
    bm25 = load_bm25_index()

    e5_hits = 0
    bm25_hits = 0
    results = []

    print(f"\n{'='*80}")
    print(f"  BM25 vs E5 — Top-{k} comparison on {len(questions)} questions")
    print(f"{'='*80}\n")

    for qi, q in enumerate(questions, 1):
        question = q["question"]
        expected_law = q.get("expected_law", "")

        e5_results = search_e5(question, model, index, k)
        bm25_results = search_bm25(question, bm25, k)

        e5_hit = check_hit(e5_results, chunks, expected_law)
        bm25_hit = check_hit(bm25_results, chunks, expected_law)
        e5_hits += e5_hit
        bm25_hits += bm25_hit

        print(f"Q{qi} [{q.get('lang','?')}]: {question}")
        print(f"  Expected: {q.get('expected_article', '?')} from {expected_law}")
        print(f"  E5  Hit@{k}: {'YES' if e5_hit else 'NO'}")
        for rank, (idx, score) in enumerate(e5_results, 1):
            src = chunks[idx]["source_file"]
            art = chunks[idx].get("article", "—")
            preview = chunks[idx]["content"][:60].replace("\n", " ")
            marker = " <--" if expected_law in src else ""
            print(f"    {rank}. [{score:.3f}] {src} art={art} | {preview}...{marker}")

        print(f"  BM25 Hit@{k}: {'YES' if bm25_hit else 'NO'}")
        for rank, (idx, score) in enumerate(bm25_results, 1):
            src = chunks[idx]["source_file"]
            art = chunks[idx].get("article", "—")
            preview = chunks[idx]["content"][:60].replace("\n", " ")
            marker = " <--" if expected_law in src else ""
            print(f"    {rank}. [{score:.3f}] {src} art={art} | {preview}...{marker}")
        print()

        results.append({
            "question": question,
            "lang": q.get("lang"),
            "expected_law": expected_law,
            "expected_article": q.get("expected_article"),
            "e5_hit": e5_hit,
            "bm25_hit": bm25_hit,
            "e5_top_k": [
                {"rank": r+1, "chunk_id": ids[idx], "source": chunks[idx]["source_file"],
                 "article": chunks[idx].get("article"), "score": score}
                for r, (idx, score) in enumerate(e5_results)
            ],
            "bm25_top_k": [
                {"rank": r+1, "chunk_id": ids[idx], "source": chunks[idx]["source_file"],
                 "article": chunks[idx].get("article"), "score": score}
                for r, (idx, score) in enumerate(bm25_results)
            ],
        })

    n = len(questions)
    print(f"{'='*80}")
    print(f"  SUMMARY: Hit@{k}")
    print(f"    E5 (semantic):  {e5_hits}/{n} ({100*e5_hits/n:.0f}%)")
    print(f"    BM25 (keyword): {bm25_hits}/{n} ({100*bm25_hits/n:.0f}%)")
    print(f"{'='*80}")

    output = {
        "k": k,
        "num_questions": n,
        "e5_hits": e5_hits,
        "bm25_hits": bm25_hits,
        "e5_hit_rate": round(e5_hits / n, 3),
        "bm25_hit_rate": round(bm25_hits / n, 3),
        "details": results,
    }
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nResults saved: {RESULTS_PATH}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare BM25 vs E5 search")
    parser.add_argument("--k", type=int, default=3, help="top-k for Hit@k (default 3)")
    parser.add_argument("--questions", type=str, help="path to questions JSON file")
    args = parser.parse_args()

    if args.questions:
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    else:
        questions = BUILTIN_QUESTIONS

    run_comparison(questions, k=args.k)


if __name__ == "__main__":
    main()
