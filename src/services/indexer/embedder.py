"""Embedder class for generating movie vectors."""

import os
from pathlib import Path
from time import perf_counter

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from FlagEmbedding import BGEM3FlagModel  # noqa: E402

from core.contracts import Movie  # noqa: E402
from core.logger import get_logger  # noqa: E402
from services.indexer.config import config  # noqa: E402
from services.indexer.schemas import IndexedMoviePoint, SparseVectorData  # noqa: E402

logger = get_logger(__name__)
LOCAL_BGE_MODEL_PATH = Path(__file__).resolve().parents[3] / "bge-m3"


class MovieEmbedder:
    """Embed movie card into vectors using the local BGE-M3 model."""

    def __init__(
        self,
        model_name: str | Path = LOCAL_BGE_MODEL_PATH,
        device: str = config.device,
        use_fp16: bool = config.use_fp16,
        batch_size: int = config.batch_size,
        sparse_min_weight: float = config.sparse_min_weight,
        min_plot_len: int = config.min_plot_length,
    ) -> None:
        model_path = str(model_name)
        logger.info(
            "Loading local BGE-M3 embedding model: path=%s device=%s fp16=%s",
            model_path,
            device,
            use_fp16,
        )
        started_at = perf_counter()
        self.model = BGEM3FlagModel(
            model_path,
            use_fp16=use_fp16,
            device=device,
        )
        self.batch_size = batch_size
        self.sparse_min_weight = sparse_min_weight
        self.min_plot_len = min_plot_len
        logger.info(
            "Embedding model loaded: path=%s duration_ms=%.1f",
            model_path,
            (perf_counter() - started_at) * 1000,
        )

    def embed_batch(self, cards: list[Movie]) -> list[IndexedMoviePoint]:
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
                    point_id=card.id,
                    plot_vector=plot_vec,
                    vibe_vector=vibe_vec,
                    sparse_vector=sparse_vec,
                    payload=card,
                )
            )

        logger.debug(
            "Embedded movie batch: cards=%d with_plot=%d duration_ms=%.1f",
            len(cards),
            len(plot_map),
            (perf_counter() - started_at) * 1000,
        )
        return points


    def _format_plot(self, card: Movie) -> str | None:
        if not card.description:
            return None
        clean = card.description.strip()
        return clean if len(clean) >= self.min_plot_len else None

    def _format_vibe(self, card: Movie) -> str:
        parts = []
        if card.genres:
            parts.append(f"Жанры: {', '.join(card.genres)}.")
        era = [card.country] if card.country else []
        if card.year is not None:
            era.append(f"{card.year // 10 * 10}-е годы")
        if era:
            parts.append(f"Страна и эпоха: {', '.join(era)}.")
        return " ".join(parts) or card.title

    def _format_sparse(self, card: Movie) -> str:
        parts = [card.title]
        if card.director:
            parts.append(card.director)
        if card.actors:
            parts.append(", ".join(card.actors))
        if card.genres:
            parts.append(", ".join(card.genres))
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
