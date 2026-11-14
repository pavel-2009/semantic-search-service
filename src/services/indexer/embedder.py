"""Embedder class for generation films vectors"""


from FlagEmbedding import BGEM3FlagModel

from services.indexer.schemas import (
    MovieCard,
    IndexedMoviePoint,
    MoviePayload,
    SparseVectorData,
)


class MovieEmbedder:
    """Embed movie card into vectors"""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cuda",
        use_fp16: bool = True,
        batch_size: int = 64,
        sparse_min_weight: float = 0.08,
        min_plot_len: int = 15,
    ):
        self.model = BGEM3FlagModel(model_name, use_fp16=use_fp16, device=device)
        self.batch_size = batch_size
        self.sparse_min_weight = sparse_min_weight
        self.min_plot_len = min_plot_len


    def embed_batch(self, cards: list[MovieCard]) -> list[IndexedMoviePoint]:
        """Embed movies into plot, vibe and NER vectors"""

        if not cards:
            print("No movies to embed")
            return []

        # Prepairing
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

        return points
