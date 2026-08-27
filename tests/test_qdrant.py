from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from semantic_search_service.core.config import settings


QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = settings.QDRANT_COLLECTION


def main() -> None:
    client = QdrantClient(url=QDRANT_URL)

    print("=== SETTINGS ===")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Model: {settings.EMBEDDING_MODEL}")
    print(f"Expected dimension: {settings.EMBEDDING_DIM}")

    print("\n=== COLLECTION ===")
    collection = client.get_collection(COLLECTION_NAME)

    print(f"Points: {collection.points_count}")
    print(f"Vector config: {collection.config.params.vectors}")

    print("\n=== MODEL ===")
    model = SentenceTransformer(settings.EMBEDDING_MODEL)

    query = "криминальная драма про мафию"

    vector = model.encode(query).tolist()

    print(f"Query: {query}")
    print(f"Vector dimension: {len(vector)}")

    print("\n=== SEARCH ===")

    result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=5,
        with_payload=True,
    )

    print(f"Results: {len(result.points)}")

    for point in result.points:
        print("\n---")
        print(f"ID: {point.id}")
        print(f"Score: {point.score}")
        print(f"Title: {point.payload.get('title')}")
        print(f"Year: {point.payload.get('year')}")
        print(f"Tags: {point.payload.get('tags')}")
        print(f"Description: {point.payload.get('description')}")


if __name__ == "__main__":
    main()