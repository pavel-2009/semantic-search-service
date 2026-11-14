"""Embedder class for generating movie vectors."""

from time import perf_counter

from FlagEmbedding import BGEM3FlagModel

from core.logger import get_logger
from services.indexer.schemas import (
    IndexedMoviePoint,
    MovieCard,
    MoviePayload,
    SparseVectorData,
)

logger = get_logger(__name__)


class MovieEmbedder:
    """Embed movie card into vectors."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cuda",
        use_fp16: bool = True,
        batch_size: int = 64,
        sparse_min_weight: float = 0.08,
        min_plot_len: int = 15,
    ) -> None:
        logger.info(
            "Loading embedding model: model=%s device=%s fp16=%s",
            model_name,
            device,
            use_fp16,
        )
        started_at = perf_counter()
        self.model = BGEM3FlagModel(model_name, use_fp16=use_fp16, device=device)
        self.batch_size = batch_size
        self.sparse_min_weight = sparse_min_weight
        self.min_plot_len = min_plot_len
        logger.info(
            "Embedding model loaded: model=%s duration_ms=%.1f",
            model_name,
            (perf_counter() - started_at) * 1000,
        )

    def embed_batch(self, cards: list[MovieCard]) -> list[IndexedMoviePoint]:
        """Embed movies into plot, vibe and NER vectors."""
        if not cards:
            logger.warning("No movies to embed")
            return []

        started_at = perf_counter()
        plot_map: dict[int, int] = {}
        dense_texts: list[str] = []
        sparse_texts: list[str] = []

        for idx, card in enumerate(cards):
            plot_str = self._format_plot(card)

            if plot_str:
                plot_map[idx] = len(dense_texts)
                dense_texts.append(plot_str)

        vibe_offset = len(dense_texts)
        for card in cards:
            dense_texts.append(self._format_vibe(card))
            sparse_texts.append(self._format_sparse(card))

        dense_out = self.model.encode(
            dense_texts,
            batch_size=self.batch_size,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )["dense_vecs"].tolist()

        sparse_out = self.model.encode(
            sparse_texts,
            batch_size=self.batch_size,
            return_dense=False,
            return_sparse=True,
            return_colbert_vecs=False,
        )["lexical_weights"]

        points: list[IndexedMoviePoint] = []

        for idx, card in enumerate(cards):
            plot_vec = dense_out[plot_map[idx]] if idx in plot_map else None
            vibe_vec = dense_out[vibe_offset + idx]
            sparse_vec = self._filter_sparse(sparse_out[idx])

            points.append(
                IndexedMoviePoint(
                    point_id=card.movie_id,
                    plot_vector=plot_vec,
                    vibe_vector=vibe_vec,
                    sparse_vector=sparse_vec,
                    payload=MoviePayload(**card.model_dump()),
                )
            )

        logger.debug(
            "Embedded movie batch: cards=%d with_plot=%d duration_ms=%.1f",
            len(cards),
            len(plot_map),
            (perf_counter() - started_at) * 1000,
        )
        return points


    def _format_plot(self, card: MovieCard) -> str | None:
        if not card.synopsis:
            return None
        clean = card.synopsis.strip()
        return clean if len(clean) >= self.min_plot_len else None

    def _format_vibe(self, card: MovieCard) -> str:
        parts = []
        if card.genres:
            parts.append(f"Жанры: {', '.join(card.genres)}.")
        if card.keywords:
            parts.append(f"Атмосфера и теги: {', '.join(card.keywords)}.")
        era = [card.country] if card.country else []
        era.append(f"{card.decade}-е годы")
        parts.append(f"Страна и эпоха: {', '.join(era)}.")
        return " ".join(parts)

    def _format_sparse(self, card: MovieCard) -> str:
        titles = f"{card.title} ({card.original_title})" if card.original_title else card.title
        parts = [titles]
        if card.directors:
            parts.append(", ".join(card.directors))
        if card.actors:
            parts.append(", ".join(card.actors))
        if card.genres or card.keywords:
            parts.append(", ".join(card.genres + card.keywords))
        return ". ".join(parts)

    def _filter_sparse(self, weights: dict) -> SparseVectorData:
        filtered = {
            int(k): float(v)
            for k, v in weights.items()
            if float(v) >= self.sparse_min_weight
        }
        return SparseVectorData(
            indices=list(filtered.keys()),
            values=list(filtered.values()),
        )
