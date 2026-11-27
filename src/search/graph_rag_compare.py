"""GraphRAG comparison: RAG-only vs RAG + Knowledge Graph context.

Runs selected questions through two pipelines:
  1. RAG-only: hybrid search → top-k chunks → LLM
  2. GraphRAG: hybrid search → top-k chunks + graph context → LLM

Uses pre-computed search results from comparison_results.json (built by
search_compare.py) so this script does NOT need faiss, sentence_transformers,
or rank_bm25 installed. The graph context comes from relations.json and
article_versions.json.

Run from the repository root:
    python src/search/graph_rag_compare.py
    python src/search/graph_rag_compare.py --model llama-3.3-70b-versatile
    python src/search/graph_rag_compare.py --dry-run   # show prompts, skip API
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CHUNKS_PATH = DATA / "processed" / "chunks.json"
SEARCH_RESULTS_PATH = DATA / "search" / "comparison_results.json"
RELATIONS_PATH = DATA / "processed" / "relations.json"
VERSIONS_PATH = DATA / "processed" / "article_versions.json"
QUESTIONS_PATH = ROOT / "eval" / "test_questions.json"
OUTPUT_PATH = DATA / "search" / "graphrag_results.json"

DEFAULT_MODEL = "openai/gpt-oss-120b"

SELECTED = [0, 10, 17, 19, 23]
# Q1  (fr) — durée de travail, art. repealed → graph should warn
# Q11 (fr) — grève, control case (no graph needed)
# Q18 (ar) — amendments 91-29 → 90-11
# Q20 (ar) — additions 22-16 → 90-11
# Q24 (ar) — durée de travail, RAG fails (retrieves repealed article)

LAW_NUM_RE = re.compile(r"(\d{2,4})\s*[-–—]\s*(\d{1,3})")
ARABIC_RE = re.compile(r"[؀-ۿ]")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_chunks() -> dict[str, dict]:
    """Load chunks keyed by chunk_id for fast lookup."""
    raw = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return {c["chunk_id"]: c for c in raw}


def load_search_results() -> dict:
    return json.loads(SEARCH_RESULTS_PATH.read_text(encoding="utf-8"))


def load_relations() -> list[dict]:
    return json.loads(RELATIONS_PATH.read_text(encoding="utf-8"))


def load_versions() -> list[dict]:
    return json.loads(VERSIONS_PATH.read_text(encoding="utf-8"))


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def detect_lang(text: str) -> str:
    arabic_chars = len(ARABIC_RE.findall(text))
    return "ar" if arabic_chars > len(text) * 0.3 else "fr"


# ---------------------------------------------------------------------------
# Graph context builder
# ---------------------------------------------------------------------------

def extract_law_number(source_file: str) -> str | None:
    """texts/1990/loi-90-11.txt → 90-11"""
    name = Path(source_file).stem
    m = LAW_NUM_RE.search(name)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def extract_law_numbers_from_text(text: str) -> list[str]:
    return [f"{m.group(1)}-{m.group(2)}" for m in LAW_NUM_RE.finditer(text)]


def build_graph_context(
    question: str,
    top_chunks: list[dict],
    relations: list[dict],
    versions: list[dict],
) -> str:
    """Build structured graph context from 1-2 hops around the question entities.

    Hop 0: law numbers in the question + law numbers in retrieved chunks.
    Hop 1: relations and version history directly involving those laws.
    Hop 2: relations that connect discovered laws back to hop-0 laws.
    """
    q_laws = set(extract_law_numbers_from_text(question))
    chunk_laws = set()
    chunk_articles: dict[str, set[str]] = {}
    for c in top_chunks:
        law = extract_law_number(c.get("source_file", c.get("source", "")))
        if law:
            chunk_laws.add(law)
            chunk_articles.setdefault(law, set()).add(c.get("article", ""))

    all_laws = q_laws | chunk_laws

    # --- Hop 1: direct relations ---
    relevant_relations = []
    discovered_laws = set()
    for r in relations:
        sl, tl = r.get("source_law", ""), r.get("target_law", "")
        if sl in all_laws or tl in all_laws:
            relevant_relations.append(r)
            discovered_laws.update((sl, tl))

    # --- Hop 2: relations connecting discovered laws to hop-0 ---
    for r in relations:
        if r in relevant_relations:
            continue
        sl, tl = r.get("source_law", ""), r.get("target_law", "")
        hop2 = discovered_laws - all_laws
        if (sl in hop2 or tl in hop2) and (sl in all_laws or tl in all_laws):
            relevant_relations.append(r)

    # --- Version history: articles in chunks, or modified by a question law ---
    relevant_versions = []
    for v in versions:
        if v["law"] not in all_laws:
            continue
        in_chunks = v["article"] in chunk_articles.get(v["law"], set())
        modified_by_q_law = any(
            any(l in ver.get("source", "") for l in q_laws)
            for ver in v.get("versions", [])
            if ver.get("action") != "original"
        )
        if in_chunks or modified_by_q_law:
            relevant_versions.append(v)

    # --- Format ---
    lang = detect_lang(question)
    summary_key = "summary_ar" if lang == "ar" else "summary_fr"
    lines = []

    if relevant_versions:
        lines.append("=== Historique des versions (article_versions.json) ===")
        for v in relevant_versions:
            status = v.get("current_status", "unknown")
            replaced = v.get("replaced_by", "")
            header = f"Article {v['article']} (loi {v['law']}): statut = {status}"
            if replaced:
                header += f" — remplacé par {replaced}"
            lines.append(header)

            for ver in v.get("versions", []):
                action = ver.get("action", "")
                source = ver.get("source", "")
                src_art = ver.get("source_article", "")
                origin = f"{source} art. {src_art}" if src_art else source
                date = ver.get("date", "")
                summary = ver.get(summary_key, ver.get("summary_fr", ""))
                lines.append(
                    f"  v{ver['version']} ({date}, {action}, source: {origin}): "
                    f"{summary[:250]}"
                )
            lines.append("")

    if relevant_relations:
        lines.append("=== Relations inter-lois (relations.json) ===")
        seen = set()
        # Prioritize relations where source or target is a question law
        def rel_priority(r: dict) -> int:
            sl, tl = r.get("source_law", ""), r.get("target_law", "")
            if sl in q_laws or tl in q_laws:
                return 0
            return 1
        for r in sorted(relevant_relations, key=rel_priority):
            key = (r["source_law"], r["relation"], r["target_law"],
                   r["target_articles"])
            if key in seen:
                continue
            seen.add(key)
            if len(seen) > 20:
                lines.append(f"  ... ({len(relevant_relations) - 20} relations supplémentaires)")
                break
            lines.append(
                f"Loi {r['source_law']} art. {r['source_article']} "
                f"--{r['relation']}--> "
                f"loi {r['target_law']} art. {r['target_articles']}"
            )

    if not lines:
        return "(aucun contexte de graphe trouvé pour cette question)"

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

CONSIGNE_RAG = """\
Tu es un assistant juridique spécialisé en droit du travail algérien.
Réponds à la question en utilisant UNIQUEMENT les passages fournis.
Cite le numéro de la loi et l'article pour chaque affirmation.
Si les passages ne contiennent pas la réponse, dis : \
« Information non disponible dans les passages fournis. »
Réponds dans la langue de la question."""

CONSIGNE_GRAPHRAG = """\
Tu es un assistant juridique spécialisé en droit du travail algérien.
Réponds à la question en utilisant les passages fournis ET le contexte \
du graphe de connaissances.
Le graphe de connaissances fournit :
- Quels articles ont été modifiés, complétés ou abrogés
- Le statut actuel des articles (en vigueur, abrogé, modifié)
- Les relations entre lois (quelle loi modifie/abroge/complète quelle autre)
IMPORTANT : si le graphe indique qu'un article a été abrogé ou remplacé, \
utilise la version en vigueur et signale l'abrogation.
Cite le numéro de la loi et l'article pour chaque affirmation.
Si les passages ne contiennent pas la réponse, dis : \
« Information non disponible dans les passages fournis. »
Réponds dans la langue de la question."""


def format_chunks_for_prompt(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        law = extract_law_number(
            c.get("source_file", c.get("source", ""))
        ) or "?"
        art = c.get("article", "?")
        lang = c.get("lang", "?")
        content = c["content"][:800]
        parts.append(
            f"[Passage {i}] loi {law}, article {art} ({lang})\n{content}"
        )
    return "\n\n".join(parts)


def build_rag_messages(question: str, chunks: list[dict]) -> list[dict]:
    passages = format_chunks_for_prompt(chunks)
    return [
        {"role": "system", "content": CONSIGNE_RAG},
        {"role": "user", "content": f"Passages :\n{passages}\n\nQuestion : {question}"},
    ]


def build_graphrag_messages(
    question: str, chunks: list[dict], graph_context: str
) -> list[dict]:
    passages = format_chunks_for_prompt(chunks)
    return [
        {"role": "system", "content": CONSIGNE_GRAPHRAG},
        {
            "role": "user",
            "content": (
                f"Passages :\n{passages}\n\n"
                f"Contexte du graphe de connaissances :\n{graph_context}\n\n"
                f"Question : {question}"
            ),
        },
    ]


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm(messages: list[dict], model: str) -> str:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def run_comparison(
    selected: list[int],
    model: str,
    dry_run: bool,
) -> list[dict]:
    print("Loading data...")
    questions = load_questions()
    chunk_map = load_chunks()
    search_results = load_search_results()
    relations = load_relations()
    versions = load_versions()
    print(
        f"  {len(chunk_map)} chunks, {len(relations)} relations, "
        f"{len(versions)} article histories"
    )

    results = []

    for qi in selected:
        q = questions[qi]
        detail = search_results["details"][qi]
        qnum = qi + 1
        question = q["question"]
        lang = q.get("lang", detect_lang(question))
        expected_law = q.get("expected_law", "")
        expected_article = q.get("expected_article", "")

        print(f"\n{'='*70}")
        print(f"Q{qnum} [{lang}]: {question}")
        print(f"  Expected: {expected_law}, {expected_article}")

        # Get top-k chunks from pre-computed hybrid results
        hybrid_top = detail.get("hybrid_top_k", [])
        top_chunks = []
        for entry in hybrid_top:
            cid = entry["chunk_id"]
            if cid in chunk_map:
                top_chunks.append(chunk_map[cid])
            else:
                top_chunks.append({
                    "chunk_id": cid,
                    "source_file": entry.get("source", ""),
                    "source": entry.get("source", ""),
                    "article": entry.get("article", ""),
                    "content": f"(chunk {cid} not found in chunks.json)",
                    "lang": lang,
                })

        print(f"  Retrieved {len(top_chunks)} chunks (from comparison_results.json):")
        for i, entry in enumerate(hybrid_top):
            print(
                f"    [{i+1}] {entry['chunk_id']}, art. {entry['article']} "
                f"(rrf={entry.get('rrf_score', 0):.4f})"
            )

        # Build graph context
        graph_context = build_graph_context(
            question, top_chunks, relations, versions
        )
        ctx_lines = graph_context.split("\n")
        print(f"\n  Graph context ({len(graph_context)} chars):")
        for line in ctx_lines[:20]:
            print(f"    {line}")
        if len(ctx_lines) > 20:
            print(f"    ... ({len(ctx_lines) - 20} more lines)")

        # Build prompts
        rag_msgs = build_rag_messages(question, top_chunks)
        graphrag_msgs = build_graphrag_messages(
            question, top_chunks, graph_context
        )

        if dry_run:
            print("\n  [DRY RUN] Skipping API calls")
            rag_answer = "(dry run)"
            graphrag_answer = "(dry run)"
        else:
            print("\n  Calling LLM (RAG-only)...")
            rag_answer = call_llm(rag_msgs, model)
            print(f"  RAG answer:\n    {rag_answer[:300]}")

            print("\n  Calling LLM (GraphRAG)...")
            graphrag_answer = call_llm(graphrag_msgs, model)
            print(f"  GraphRAG answer:\n    {graphrag_answer[:300]}")

        results.append({
            "question_number": qnum,
            "question": question,
            "lang": lang,
            "expected_law": expected_law,
            "expected_article": expected_article,
            "hybrid_hit": detail.get("hybrid_hit", None),
            "hybrid_rank": detail.get("hybrid_rank", None),
            "retrieved_chunks": [
                {
                    "chunk_id": e["chunk_id"],
                    "source": e.get("source", ""),
                    "article": e.get("article", ""),
                    "rrf_score": e.get("rrf_score", 0),
                }
                for e in hybrid_top
            ],
            "graph_context": graph_context,
            "rag_answer": rag_answer,
            "graphrag_answer": graphrag_answer,
        })

    return results


def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*70}")
    print("RÉSUMÉ : RAG vs GraphRAG")
    print(f"{'='*70}\n")

    for r in results:
        qnum = f"Q{r['question_number']}"
        hit = "✓" if r["hybrid_hit"] else "✗"
        expected = f"{r['expected_law']}, {r['expected_article']}"

        print(f"{qnum} [{r['lang']}] — RAG Hit@3: {hit} (rank {r['hybrid_rank']})")
        print(f"  Expected: {expected}")
        print(f"  RAG:      {r['rag_answer'][:150]}")
        print(f"  GraphRAG: {r['graphrag_answer'][:150]}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="GraphRAG comparison")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Groq model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompts and graph context, skip API calls")
    parser.add_argument(
        "--questions", type=int, nargs="*", default=None,
        help="0-indexed question positions (default: 0 10 17 19 23)"
    )
    args = parser.parse_args()

    selected = args.questions if args.questions is not None else SELECTED

    if not args.dry_run:
        if not os.environ.get("GROQ_API_KEY"):
            try:
                from dotenv import load_dotenv
                load_dotenv(ROOT / ".env")
            except ImportError:
                pass
        if not os.environ.get("GROQ_API_KEY"):
            print("Error: GROQ_API_KEY not set. Add it to .env or export it.")
            sys.exit(1)

    results = run_comparison(selected, args.model, args.dry_run)

    print_summary(results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Results saved to {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
