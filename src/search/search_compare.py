"""Compare BM25 vs E5 vs Hybrid search on test questions.

Loads both indices built by build_index.py, runs queries, prints side-by-side
top-k results with ranks, and computes Hit@k and MRR for each method.

Run from the repository root:
    python src/search/search_compare.py
    python src/search/search_compare.py --k 5
    python src/search/search_compare.py --questions path/to/questions.json
    python src/search/search_compare.py --alpha 0.3 0.5 0.7
"""
from __future__ import annotations

import argparse
import json
import re
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
RRF_K = 60

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


ARABIC_RE = re.compile(r"[؀-ۿ]")
LEGAL_REF_RE = re.compile(r"(\d{1,3})\s*[-–—]\s*(\d{1,3})")

ALPHA_FR = 0.7
ALPHA_AR = 0.3


def detect_lang(text: str) -> str:
    arabic_chars = len(ARABIC_RE.findall(text))
    return "ar" if arabic_chars > len(text) * 0.3 else "fr"


def extract_legal_refs(text: str) -> list[str]:
    """Pull law-number tokens like '22-16', '90-11' from a query."""
    return [f"{m.group(1)}-{m.group(2)}" for m in LEGAL_REF_RE.finditer(text)]


def tokenize(text: str) -> list[str]:
    text = re.sub(r"(\d+)\s*[-–—]\s*(\d+)", r"\1-\2", text.lower())
    return re.findall(r"\w+(?:[-']\w+)*", text)

def search_e5(
    query: str, model: SentenceTransformer, index: faiss.IndexFlatIP, k: int
) -> list[tuple[int, float]]:
    q_emb = model.encode(
        [f"query: {query}"], normalize_embeddings=True
    ).astype(np.float32)
    scores, indices = index.search(q_emb, k)
    return [(int(indices[0][i]), float(scores[0][i])) for i in range(k)]


def search_bm25(
    query: str, bm25: BM25Okapi, k: int
) -> list[tuple[int, float]]:
    tokens = tokenize(query)
    scores = bm25.get_scores(tokens)
    top_k = np.argsort(scores)[::-1][:k]
    return [(int(i), float(scores[i])) for i in top_k]


def search_bm25_refs(
    refs: list[str], bm25: BM25Okapi, k: int
) -> list[tuple[int, float]]:
    """BM25 search using only the extracted legal references (numbers)."""
    if not refs:
        return []
    scores = bm25.get_scores(refs)
    top_k = np.argsort(scores)[::-1][:k]
    return [(int(i), float(scores[i])) for i in top_k if scores[i] > 0]


def search_hybrid(
    query: str,
    model: SentenceTransformer,
    index: faiss.IndexFlatIP,
    bm25: BM25Okapi,
    k: int,
    alpha: float = 0.5,
    retrieval_depth: int = 50,
    auto_alpha: bool = False,
) -> list[tuple[int, float]]:
    if auto_alpha:
        alpha = ALPHA_AR if detect_lang(query) == "ar" else ALPHA_FR

    bm25_results = search_bm25(query, bm25, retrieval_depth)
    e5_results = search_e5(query, model, index, retrieval_depth)

    rrf_scores: dict[int, float] = {}

    for rank, (idx, _) in enumerate(bm25_results):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + alpha / (RRF_K + rank + 1)

    for rank, (idx, _) in enumerate(e5_results):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + (1 - alpha) / (RRF_K + rank + 1)

    refs = extract_legal_refs(query)
    if refs:
        ref_results = search_bm25_refs(refs, bm25, retrieval_depth)
        ref_weight = 0.3
        for rank, (idx, _) in enumerate(ref_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + ref_weight / (RRF_K + rank + 1)

    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results[:k]


def find_rank(results: list[tuple[int, float]], chunks: list[dict], expected_law: str) -> int | None:
    if not expected_law or expected_law.startswith("__"):
        return None
    laws = [l.strip() for l in expected_law.split(",")]
    for rank, (idx, _) in enumerate(results, 1):
        source = chunks[idx].get("source_file", "")
        if any(law in source for law in laws):
            return rank
    return None


def check_hit(results: list[tuple[int, float]], chunks: list[dict], expected_law: str) -> bool:
    if not expected_law or expected_law.startswith("__"):
        return False
    laws = [l.strip() for l in expected_law.split(",")]
    for idx, _ in results:
        source = chunks[idx].get("source_file", "")
        if any(law in source for law in laws):
            return True
    return False


def run_comparison(questions: list[dict], k: int, alpha: float,
                   auto_alpha: bool = False) -> dict:
    chunks = load_chunks()
    ids = load_ids()

    n_chunks = len(chunks)
    print(f"Loaded {n_chunks} chunks")

    index, model = load_e5_index()
    if index.ntotal != n_chunks:
        print(f"WARNING: FAISS has {index.ntotal} vectors but chunks.json has {n_chunks}")
        print("Run build_index.py first to rebuild indices.")
        return {}

    bm25 = load_bm25_index()

    e5_hits = 0
    bm25_hits = 0
    hybrid_hits = 0
    e5_ranks = []
    bm25_ranks = []
    hybrid_ranks = []
    results = []

    rank_depth = max(k, 5)

    alpha_label = f"auto: fr={ALPHA_FR}/ar={ALPHA_AR}" if auto_alpha else str(alpha)
    print(f"\n{'='*80}")
    print(f"  BM25 vs E5 vs Hybrid (alpha={alpha_label}) — Top-{k} on {len(questions)} questions")
    if auto_alpha:
        print(f"  + cross-language legal-ref boost on number-bearing queries")
    print(f"{'='*80}\n")

    for qi, q in enumerate(questions, 1):
        question = q["question"]
        expected_law = q.get("expected_law", "")

        e5_results = search_e5(question, model, index, rank_depth)
        bm25_results = search_bm25(question, bm25, rank_depth)
        hybrid_results = search_hybrid(question, model, index, bm25, rank_depth,
                                       alpha=alpha, auto_alpha=auto_alpha)

        e5_hit = check_hit(e5_results[:k], chunks, expected_law)
        bm25_hit = check_hit(bm25_results[:k], chunks, expected_law)
        hybrid_hit = check_hit(hybrid_results[:k], chunks, expected_law)

        e5_rank = find_rank(e5_results, chunks, expected_law)
        bm25_rank = find_rank(bm25_results, chunks, expected_law)
        hybrid_rank = find_rank(hybrid_results, chunks, expected_law)

        e5_hits += e5_hit
        bm25_hits += bm25_hit
        hybrid_hits += hybrid_hit
        if e5_rank: e5_ranks.append(e5_rank)
        if bm25_rank: bm25_ranks.append(bm25_rank)
        if hybrid_rank: hybrid_ranks.append(hybrid_rank)

        e5_r = str(e5_rank) if e5_rank else "—"
        bm25_r = str(bm25_rank) if bm25_rank else "—"
        hyb_r = str(hybrid_rank) if hybrid_rank else "—"
        e5_tag = "YES" if e5_hit else "NO "
        bm25_tag = "YES" if bm25_hit else "NO "
        hyb_tag = "YES" if hybrid_hit else "NO "

        q_lang = detect_lang(question)
        refs = extract_legal_refs(question)
        alpha_used = (ALPHA_AR if q_lang == "ar" else ALPHA_FR) if auto_alpha else alpha
        ref_tag = f" refs={','.join(refs)}" if refs and auto_alpha else ""
        print(f"Q{qi:>2} [{q_lang:>2}]  E5={e5_tag}(r{e5_r})  BM25={bm25_tag}(r{bm25_r})  Hybrid={hyb_tag}(r{hyb_r})  a={alpha_used}{ref_tag}  | {question[:50]}")

        results.append({
            "question": question,
            "lang": q.get("lang"),
            "expected_law": expected_law,
            "expected_article": q.get("expected_article"),
            "e5_hit": e5_hit,
            "bm25_hit": bm25_hit,
            "hybrid_hit": hybrid_hit,
            "e5_rank": e5_rank,
            "bm25_rank": bm25_rank,
            "hybrid_rank": hybrid_rank,
            "e5_top_k": [
                {"rank": r+1, "chunk_id": ids[idx], "source": chunks[idx]["source_file"],
                 "article": chunks[idx].get("article"), "score": score}
                for r, (idx, score) in enumerate(e5_results[:k])
            ],
            "bm25_top_k": [
                {"rank": r+1, "chunk_id": ids[idx], "source": chunks[idx]["source_file"],
                 "article": chunks[idx].get("article"), "score": score}
                for r, (idx, score) in enumerate(bm25_results[:k])
            ],
            "hybrid_top_k": [
                {"rank": r+1, "chunk_id": ids[idx], "source": chunks[idx]["source_file"],
                 "article": chunks[idx].get("article"), "rrf_score": round(score, 6)}
                for r, (idx, score) in enumerate(hybrid_results[:k])
            ],
        })

    n = len(questions)
    e5_mrr = sum(1 / r for r in e5_ranks) / n if e5_ranks else 0
    bm25_mrr = sum(1 / r for r in bm25_ranks) / n if bm25_ranks else 0
    hybrid_mrr = sum(1 / r for r in hybrid_ranks) / n if hybrid_ranks else 0

    print(f"\n{'='*80}")
    print(f"  SUMMARY  Hit@{k} (alpha={alpha}):")
    print(f"    E5 (semantic):  {e5_hits:>2}/{n} ({100*e5_hits/n:.0f}%)")
    print(f"    BM25 (keyword): {bm25_hits:>2}/{n} ({100*bm25_hits/n:.0f}%)")
    print(f"    Hybrid (RRF):   {hybrid_hits:>2}/{n} ({100*hybrid_hits/n:.0f}%)")
    print(f"\n  MRR (Mean Reciprocal Rank) — higher = better:")
    print(f"    E5:     {e5_mrr:.4f}")
    print(f"    BM25:   {bm25_mrr:.4f}")
    print(f"    Hybrid: {hybrid_mrr:.4f}")
    print(f"{'='*80}")

    output = {
        "k": k,
        "alpha": alpha,
        "num_questions": n,
        "e5_hits": e5_hits,
        "bm25_hits": bm25_hits,
        "hybrid_hits": hybrid_hits,
        "e5_hit_rate": round(e5_hits / n, 3),
        "bm25_hit_rate": round(bm25_hits / n, 3),
        "hybrid_hit_rate": round(hybrid_hits / n, 3),
        "e5_mrr": round(e5_mrr, 4),
        "bm25_mrr": round(bm25_mrr, 4),
        "hybrid_mrr": round(hybrid_mrr, 4),
        "details": results,
    }
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nResults saved: {RESULTS_PATH}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare BM25 vs E5 vs Hybrid search")
    parser.add_argument("--k", type=int, default=3, help="top-k for Hit@k (default 3)")
    parser.add_argument("--questions", type=str, help="path to questions JSON file")
    parser.add_argument("--alpha", type=float, default=0.5,
                        help="BM25 weight in hybrid RRF (default 0.5)")
    parser.add_argument("--auto-alpha", action="store_true",
                        help="auto-tune alpha by query language (fr=0.7, ar=0.3) "
                             "+ cross-language legal-ref boost")
    args = parser.parse_args()

    if args.questions:
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    else:
        questions = BUILTIN_QUESTIONS

    run_comparison(questions, k=args.k, alpha=args.alpha,
                   auto_alpha=args.auto_alpha)


if __name__ == "__main__":
    main()
