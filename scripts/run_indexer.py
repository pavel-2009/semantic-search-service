"""Script for running the Qdrant indexer."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from core.config import settings  # noqa: E402
from services.indexer import Indexer  # noqa: E402


def main() -> None:
    """Run the indexer and print the resulting collection statistics."""
    print("=" * 60)
    print("🚀 ЗАПУСК ИНДЕКСАТОРА")
    print("=" * 60)
    print(f"📁 Данные: {settings.DATA_PATH}")
    print(f"💾 Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    print(f"📚 Коллекция: {settings.QDRANT_COLLECTION}")
    print(f"🧠 Модель: {settings.EMBEDDING_MODEL}")
    print(f"📦 Batch size: {settings.BATCH_SIZE}")
    print("=" * 60)

    indexer = Indexer()
    indexer.create_collection(force_recreate=True)
    indexer.index_movies(filepath=settings.DATA_PATH, batch_size=settings.BATCH_SIZE)

    stats = indexer.get_stats()
    print("\n📊 СТАТИСТИКА ПОСЛЕ ИНДЕКСАЦИИ:")
    print(f"  Точки: {stats.points_count}")
    print(f"  Статус: {stats.status}")
    print("\n✅ Индексация завершена успешно!")


if __name__ == "__main__":
    main()
