"""Indexer config."""

from dataclasses import dataclass
from pathlib import Path

from src.core.device import get_compute_device

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DEVICE = get_compute_device()


@dataclass(frozen=True)
class IndexerConfig:
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "movies"
    model_name: str = str(PROJECT_ROOT / "bge-m3")
    device: str = DEFAULT_DEVICE
    use_fp16: bool = DEFAULT_DEVICE == "cuda"
    dense_dim: int = 1024
    sparse_min_weight: float = 0.08
    batch_size: int = 8 if DEFAULT_DEVICE == "mps" else 64
    min_plot_length: int = 15
    dataset_path: Path = PROJECT_ROOT / "src" / "scraper" / "data" / "movies_enriched.jsonl"


config = IndexerConfig()
