"""Indexer config."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class IndexerConfig:
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "movies"
    model_name: str = str(PROJECT_ROOT / "bge-m3")
    device: str = "cuda"
    use_fp16: bool = True
    dense_dim: int = 1024
    sparse_min_weight: float = 0.08
    batch_size: int = 64
    min_plot_length: int = 15
    dataset_path: Path = PROJECT_ROOT / "src" / "scraper" / "data" / "movies.jsonl"


config = IndexerConfig()
