"""Indexer config."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IndexerConfig:
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "movies"
    model_name: str = "BAAI/bge-m3"
    device: str = "cuda"
    use_fp16: bool = True
    dense_dim: int = 1024
    sparse_min_weight: float = 0.08
    batch_size: int = 64
    min_plot_length: int = 15
    dataset_path: Path = (
        Path(__file__).resolve().parent.parent.parent / "scraper" / "data" / "movies_dataset.jsonl"
    )


config = IndexerConfig()
