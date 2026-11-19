"""Search service entrypoint."""

from typing import Any

from src.services.search_service.ranking.ranking import RerankingService
from src.services.search_service.ranking.schemas import RerankingRequest, RerankingResponse
from src.services.search_service.schemas import SearchQuery, SearchResponse, ParsedQuery, EncodedQuery
from src.services.search_service.parsing.text_parser import TextParser, ParsedText
from src.services.search_service.embedder.schemas import EmbedderResponse
from src.repositories.qdrant_repository import QdrantRepository
from src.repositories.schemas import RetrievalResponse
from src.services.indexer.embedder import MovieEmbedder


class SearchService:
    """Search service entrypoint."""

    def __init__(
        self,
        parser: TextParser,
        embedder: MovieEmbedder,
        qdrant_repo: QdrantRepository,
        reranker: RerankingService,
    ) -> None:
        self.parser = parser
        self.embedder = embedder
        self.qdrant_repo = qdrant_repo
        self.reranker = reranker

    def search(self, query: SearchQuery) -> SearchResponse:
        """Search for movies based on the query."""
        parsed_query: ParsedText = self.parser.parse(query.text)
        encoded_query: EmbedderResponse = self.embedder.embed_request(parsed_query)

        retrieval_response: RetrievalResponse = self.qdrant_repo.get_points(encoded_query, query.top_k)

        reranking_request: RerankingRequest = RerankingRequest(
            query=query.text,
            documents=retrieval_response.response,
        )

        reranking_response: RerankingResponse = self.reranker.rerank(reranking_request, query.top_k)

        return SearchResponse(documents=reranking_response.reranked_documents)
