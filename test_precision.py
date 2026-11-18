"""Reranking Precision@K evaluation."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from ranx import Qrels, Run, evaluate

DATASET_PATH = Path(__file__).resolve().parent / "eval_dataset" / "recall_dataset.json"
METRICS = ["precision@5", "precision@10"]


def load_queries() -> list[dict]:
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return data["queries"]


def document_text(payload: dict) -> str:
    parts = [
        str(payload.get("title") or ""),
        str(payload.get("year") or ""),
        " ".join(payload.get("genres") or []),
        " ".join(payload.get("moods") or []),
        str(payload.get("description") or ""),
    ]
    return ". ".join(part for part in parts if part)


def build_reranked_run(documents_by_query: dict[str, list[dict]]) -> dict[str, dict[str, float]]:
    return {
        qid: {
            str(document["id"]): float(len(documents) - rank)
            for rank, document in enumerate(documents)
        }
        for qid, documents in documents_by_query.items()
    }


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "0"

    from src.repositories.qdrant_repository import QdrantRepository
    from src.services.indexer.embedder import MovieEmbedder
    from src.services.search_service.parsing.text_parser import TextParser
    from src.services.search_service.ranking.ranking import RerankingService
    from src.services.search_service.ranking.schemas import RerankingRequest

    queries = load_queries()

    parser = TextParser()
    embedder = MovieEmbedder()
    repo = QdrantRepository()
    reranker = RerankingService()

    qrels_dict: dict[str, dict[str, int]] = {}
    reranked_run: dict[str, dict[str, float]] = {}
    by_category: dict[str, list[str]] = defaultdict(list)

    for item in queries:
        qid = item["id"]
        qrels_dict[qid] = {str(mid): int(rel) for mid, rel in item["qrels"].items()}
        by_category[item["category"]].append(qid)

        parsed = parser.parse(item["query"])
        embeddings = embedder.embed_request(parsed)
        retrieval = repo.get_points(embeddings=embeddings)

        documents = [
            {
                "id": str(point.id),
                "text": document_text(point.payload or {}),
            }
            for point in retrieval.response
        ]
        reranked = reranker.rerank(
            RerankingRequest(query=item["query"], documents=documents)
        )

        reranked_run[qid] = {
            str(document["id"]): float(len(reranked.reranked_documents) - rank)
            for rank, document in enumerate(reranked.reranked_documents)
        }

    qrels = Qrels(qrels_dict)
    reranking = Run(reranked_run)

    overall = evaluate(qrels, reranking, metrics=METRICS)
    print("=== Reranking Precision@K ===")
    for metric, score in overall.items():
        print(f"  {metric:<10}: {score:.4f}")

    print("\n=== Precision by Category ===")
    for category, qids in by_category.items():
        cat_qrels = Qrels({qid: qrels_dict[qid] for qid in qids})
        cat_run = Run({qid: reranked_run[qid] for qid in qids})
        scores = evaluate(cat_qrels, cat_run, metrics=METRICS)
        print(
            f"  {category:<16} (n={len(qids):2d}): "
            f"precision@5={scores['precision@5']:.4f}  "
            f"precision@10={scores['precision@10']:.4f}"
        )


if __name__ == "__main__":
    main()
