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

from src.core.contracts import EnrichedMovie
from src.core.logger import get_logger  # noqa: E402
from src.core.vibe import format_vibe  # noqa: E402
from src.core.config import settings  # noqa: E402
from src.services.indexer.schemas import IndexedMoviePoint, SparseVectorData  # noqa: E402
from src.services.search_service.parsing import ParsedText  # noqa: E402
from src.services.search_service.embedder.schemas import EmbedderResponse  # noqa: E402

logger = get_logger(__name__)
LOCAL_BGE_MODEL_PATH = Path(__file__).resolve().parents[3] / "bge-m3"


class MovieEmbedder:
    """Embed movie card into vectors using the local BGE-M3 model."""

    def __init__(
        self,
        model_name: str | Path = LOCAL_BGE_MODEL_PATH,
        device: str = settings.COMPUTE_DEVICE,
        use_fp16: bool = settings.EMBEDDING_USE_FP16,
        batch_size: int = settings.INDEX_BATCH_SIZE,
        sparse_min_weight: float = settings.SPARSE_MIN_WEIGHT,
        min_plot_len: int = settings.MIN_PLOT_LENGTH,
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
        self.model_name = model_path
        self.batch_size = batch_size
        self.sparse_min_weight = sparse_min_weight
        self.min_plot_len = min_plot_len
        logger.info(
            "Embedding model loaded: path=%s duration_ms=%.1f",
            model_path,
            (perf_counter() - started_at) * 1000,
        )

    def embed_cards(self, cards: list[EnrichedMovie]) -> list[IndexedMoviePoint]:
        """Embed enriched movies into plot, vibe and sparse vectors."""
        if not cards:
            logger.warning("No movies to embed")
            return []

        started_at = perf_counter()
        plot_map: dict[int, int] = {}
        vibe_map: dict[int, int] = {}
        dense_texts: list[str] = []

        for idx, card in enumerate(cards):
            if plot_str := self._format_plot(card):
                plot_map[idx] = len(dense_texts)
                dense_texts.append(plot_str)
            if vibe_str := self._format_vibe(card):
                vibe_map[idx] = len(dense_texts)
                dense_texts.append(vibe_str)
        sparse_texts = [self._format_sparse(card) for card in cards]

        dense_out = self.model.encode(
            dense_texts,
            batch_size=self.batch_size,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )["dense_vecs"].tolist() if dense_texts else []

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
            vibe_vec = dense_out[vibe_map[idx]] if idx in vibe_map else None
            sparse_vec = self._filter_sparse(sparse_out[idx])

            points.append(
                IndexedMoviePoint(
                    point_id=card.id,
                    plot_vector=plot_vec,
                    vibe_vector=vibe_vec,
                    sparse_vector=sparse_vec,
                    payload=card.to_movie_payload(),
                )
            )

        logger.debug(
            "Embedded movie batch: cards=%d with_plot=%d with_vibe=%d duration_ms=%.1f",
            len(cards),
            len(plot_map),
            len(vibe_map),
            (perf_counter() - started_at) * 1000,
        )
        return points

    def embed_request(self, request: ParsedText) -> EmbedderResponse:
        """Embed parsed plot and vibe text densely and entities sparsely."""
        started_at = perf_counter()
        dense_names: list[str] = []
        dense_texts: list[str] = []

        for name, text in (("plot", request.plot), ("vibe", request.vibe)):
            if text and text.strip():
                dense_names.append(name)
                dense_texts.append(text.strip())

        dense_embeddings = (
            self.model.encode(
                dense_texts,
                batch_size=self.batch_size,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )["dense_vecs"].tolist()
            if dense_texts
            else []
        )

        sparse_text = request.entities.strip() if request.entities else ""
        sparse_weights = (
            self.model.encode(
                [sparse_text],
                batch_size=self.batch_size,
                return_dense=False,
                return_sparse=True,
                return_colbert_vecs=False,
            )["lexical_weights"][0]
            if sparse_text
            else {}
        )

        if not dense_texts and not sparse_text:
            logger.warning("No text to embed in request")

        logger.debug(
            "Embedded search request: dense=%d sparse=%s duration_ms=%.1f",
            len(dense_embeddings),
            bool(sparse_text),
            (perf_counter() - started_at) * 1000,
        )
        filters = request.filter or {}
        return EmbedderResponse(
            embeddings=dense_embeddings,
            embedding_names=dense_names,
            sparse_vector=self._filter_sparse(sparse_weights),
            model=self.model_name,
            year_range=(
                int(filters.get("year_gte", 0)),
                int(filters.get("year_lte", 0)),
            ),
            rating_range=(
                float(filters.get("rating_gte", 0)),
                float(filters.get("rating_lte", 0)),
            ),
        )

    def _format_plot(self, card: EnrichedMovie) -> str | None:
        raw = card.indexing.plot if card.indexing.plot is not None else card.description
        if not raw:
            return None
        clean = raw.strip()
        return clean if len(clean) >= self.min_plot_len else None

    def _format_vibe(self, card: EnrichedMovie) -> str | None:
        if card.indexing.vibe and card.indexing.vibe.strip():
            return card.indexing.vibe.strip()
        return format_vibe(card.moods)

    def _format_sparse(self, card: EnrichedMovie) -> str:
        if card.indexing.entities and card.indexing.entities.strip():
            return card.indexing.entities.strip()
        return ". ".join(part for part in (card.title, *card.genres) if part)

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
