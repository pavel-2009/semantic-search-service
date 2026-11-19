"""Retrieval Recall@K evaluation."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ranx import Qrels, Run, evaluate

from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.embedder import MovieEmbedder
from src.services.search_service.parsing.text_parser import TextParser
DATASET_PATH = Path(__file__).resolve().parent / "eval_dataset" / "recall_dataset.json"
RECALL_METRICS = ["recall@5", "recall@10", "recall@20", "recall@30"]


def load_dataset(path: Path = DATASET_PATH) -> list[dict]:
    """Load evaluation queries and qrels from JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["queries"]


def main() -> None:
    queries = load_dataset()

    parser = TextParser()
    embedder = MovieEmbedder()
    repo = QdrantRepository()

    qrels_dict: dict[str, dict[str, int]] = {}
    retrieval_run: dict[str, dict[str, float]] = {}
    by_category: dict[str, list[str]] = defaultdict(list)

    for item in queries:
        qid = item["id"]
        qrels_dict[qid] = {str(mid): int(rel) for mid, rel in item["qrels"].items()}
        by_category[item["category"]].append(qid)

        parsed = parser.parse(item["query"])
        embeddings = embedder.embed_request(parsed)
        retrieval = repo.get_points(embeddings=embeddings)

        retrieved_points = retrieval.response
        retrieval_run[qid] = {
            str(point.id): float(point.score)
            for point in retrieved_points
        }

    qrels = Qrels(qrels_dict)
    retrieval = Run(retrieval_run)
    overall_recall = evaluate(qrels, retrieval, metrics=RECALL_METRICS)
    print("=== Retrieval Recall@K ===")
    for metric, score in overall_recall.items():
        print(f"  {metric:<10}: {score:.4f}")

    print("\n=== Recall by Category ===")
    for category, qids in by_category.items():
        cat_qrels = Qrels({qid: qrels_dict[qid] for qid in qids})
        cat_retrieval = Run({qid: retrieval_run[qid] for qid in qids})
        cat_recall = evaluate(
            cat_qrels,
            cat_retrieval,
            metrics=["recall@10", "recall@30"],
        )
        print(
            f"  {category:<16} (n={len(qids):2d}): "
            f"recall@10={cat_recall['recall@10']:.4f}  "
            f"recall@30={cat_recall['recall@30']:.4f}"
        )

    # Per-query misses at @30 for quick diagnostics
    misses: list[tuple[str, float, str]] = []
    for item in queries:
        qid = item["id"]
        expected = set(qrels_dict[qid])
        top_30 = sorted(
            retrieval_run[qid].items(),
            key=lambda result: result[1],
            reverse=True,
        )[:30]
        retrieved = {point_id for point_id, _ in top_30}
        hit_ratio = len(expected & retrieved) / len(expected)
        if hit_ratio < 1.0:
            misses.append((qid, hit_ratio, item["query"]))

    print(f"\nQueries with Recall@30 < 1.0: {len(misses)}/{len(queries)}")
    for qid, ratio, query_text in misses[:10]:
        print(f"  [{qid}] {ratio:.2f} | {query_text}")


if __name__ == "__main__":
    main()
