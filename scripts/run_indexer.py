"""Script for running the Qdrant indexer."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from services.indexer.config import config  # noqa: E402
from services.indexer.indexer import Indexer  # noqa: E402


def main() -> None:
    """Run the indexer and print the resulting collection statistics."""
    print("=" * 60)
    print("🚀 ЗАПУСК ИНДЕКСАТОРА")
    print("=" * 60)
    print(f"📁 Данные: {config.dataset_path}")
    print(f"💾 Qdrant: {config.qdrant_url}")
    print(f"📚 Коллекция: {config.collection_name}")
    print(f"🧠 Модель: {config.model_name}")
    print(f"📦 Batch size: {config.batch_size}")
    print("=" * 60)

    indexer = Indexer()
    indexer.index_movies(
        filepath=config.dataset_path,
        batch_size=config.batch_size,
        force_recreate=True,
    )

    stats = indexer.get_stats()
    print("\n📊 СТАТИСТИКА ПОСЛЕ ИНДЕКСАЦИИ:")
    print(f"  Точки: {stats.points_count}")
    print(f"  Статус: {stats.status}")
    print("\n✅ Индексация завершена успешно!")


if __name__ == "__main__":
    main()
