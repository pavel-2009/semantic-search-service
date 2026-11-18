"""Reranking Precision@K evaluation."""

from __future__ import annotations

import json
import os
from pathlib import Path

from ranx import Qrels, Run, evaluate

DATASET_PATH = Path(__file__).resolve().parent / "eval_dataset" / "recall_dataset.json"
METRICS = ["precision@5", "precision@10"]


def load_queries() -> list[dict]:
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return [
        item for item in data["queries"]
    ]


def document_text(payload: dict) -> str:
    fields = [
        ("Название", payload.get("title")),
        ("Год", payload.get("year")),
        ("Страны", ", ".join(payload.get("countries") or [])),
        ("Жанры", ", ".join(payload.get("genres") or [])),
        ("Настроение", ", ".join(payload.get("moods") or [])),
        ("Рейтинг", payload.get("rating")),
        ("Сюжет", payload.get("description")),
    ]
    return ". ".join(
        f"{label}: {str(value).strip()}"
        for label, value in fields
        if value is not None and str(value).strip()
    )


def print_rank_changes(
    query: str,
    documents: list[dict],
    reranked_documents: list[dict],
) -> None:
    initial_positions = {
        str(document["id"]): rank
        for rank, document in enumerate(documents, start=1)
    }

    print(f"\nЗапрос: {query}")
    print("Поиск -> CrossEncoder:")
    for new_rank, document in enumerate(reranked_documents, start=1):
        movie = str(document.get("title") or "Без названия")
        if year := document.get("year"):
            movie += f" ({year})"
        movie_id = str(document["id"])
        old_rank = initial_positions.get(movie_id, "—")
        print(f"  {old_rank:>2} -> {new_rank:>2}  {movie} [id={movie_id}]")


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
    if not queries:
        raise ValueError("No queries found in the dataset. Please check the dataset file.")

    parser = TextParser()
    embedder = MovieEmbedder()
    repo = QdrantRepository()
    reranker = RerankingService()

    qrels_dict: dict[str, dict[str, int]] = {}
    reranked_run: dict[str, dict[str, float]] = {}

    for item in queries:
        qid = item["id"]
        qrels_dict[qid] = {str(mid): int(rel) for mid, rel in item["qrels"].items()}

        parsed = parser.parse(item["query"])
        embeddings = embedder.embed_request(parsed)
        retrieval = repo.get_points(embeddings=embeddings)

        documents = []
        for point in retrieval.response:
            payload = point.payload or {}
            documents.append(
                {
                    "id": str(point.id),
                    "title": payload.get("title"),
                    "year": payload.get("year"),
                    "text": document_text(payload),
                }
            )
        reranked = reranker.rerank(
            RerankingRequest(query=item["query"], documents=documents)
        )
        print_rank_changes(
            item["query"],
            documents,
            reranked.reranked_documents,
        )

        reranked_run[qid] = {
            str(document["id"]): float(len(reranked.reranked_documents) - rank)
            for rank, document in enumerate(reranked.reranked_documents)
        }

    qrels = Qrels(qrels_dict)
    reranking = Run(reranked_run)

    overall = evaluate(qrels, reranking, metrics=METRICS)
    print(f"=== Reranking Precision@K: (n={len(queries)}) ===")
    for category in set(item.get("category") for item in queries):
        category_qids = [item["id"] for item in queries if item.get("category") == category]
        category_qrels = Qrels({qid: qrels_dict[qid] for qid in category_qids})
        category_reranking = Run({qid: reranked_run[qid] for qid in category_qids})
        category_overall = evaluate(category_qrels, category_reranking, metrics=METRICS)
        print(f"=== Category: {category} (n={len(category_qids)}) ===")
        for metric, score in category_overall.items():
            print(f"  {metric:<10}: {score:.4f}\n")

    # Print overall metrics
    print("\n\n=== Overall Metrics ===\n\n")
    for metric, score in overall.items():
        print(f"  {metric:<10}: {score:.4f}")


if __name__ == "__main__":
    main()
