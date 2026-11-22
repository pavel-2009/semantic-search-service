"""Search service entrypoint."""

from time import perf_counter

from src.core.telemetry import (
    search_requests_total,
    search_results_count,
    search_stage_duration_ms,
)
from src.services.search_service.ranking.ranking import RerankingService
from src.services.search_service.ranking.schemas import RerankingRequest, RerankingResponse
from src.services.search_service.schemas import SearchQuery, SearchResponse
from src.services.search_service.parsing.text_parser import ParsedText, TextParser
from src.services.search_service.embedder.schemas import EmbedderResponse
from src.repositories.qdrant_repository import QdrantRepository
from src.repositories.schemas import RetrievalResponse
from src.services.indexer.embedder import MovieEmbedder
from src.core.telemetry import get_tracer


tracer = get_tracer()


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
        total_start = perf_counter()
        status = "ok"
        try:
            with tracer.start_as_current_span("search") as span:
                span.set_attribute("query", query.text)
                span.set_attribute("top_k", query.top_k)
                span.set_attribute("filters", str(query.filters))

                with tracer.start_as_current_span("parse"):
                    stage_start = perf_counter()
                    parsed_query: ParsedText = self.parser.parse(query.text)
                    if query.filters:
                        parsed_query.filter = {
                            **(parsed_query.filter or {}),
                            **query.filters,
                        }
                    search_stage_duration_ms.record(
                        (perf_counter() - stage_start) * 1000, {"stage": "parse"}
                    )

                stage_start = perf_counter()
                encoded_query: EmbedderResponse = self.embedder.embed_request(parsed_query)
                search_stage_duration_ms.record(
                    (perf_counter() - stage_start) * 1000, {"stage": "embed"}
                )

                stage_start = perf_counter()
                retrieval_response: RetrievalResponse = self.qdrant_repo.get_points(
                    encoded_query, query.top_k
                )
                search_stage_duration_ms.record(
                    (perf_counter() - stage_start) * 1000, {"stage": "retrieve"}
                )

                stage_start = perf_counter()
                reranking_request: RerankingRequest = RerankingRequest(
                    query=query.text,
                    documents=retrieval_response.response,
                )
                reranking_response: RerankingResponse = self.reranker.rerank(
                    reranking_request, query.top_k
                )
                search_stage_duration_ms.record(
                    (perf_counter() - stage_start) * 1000, {"stage": "rerank"}
                )

                search_results_count.record(
                    len(reranking_response.reranked_documents)
                )
                return SearchResponse(
                    documents=reranking_response.reranked_documents
                )
        except Exception:
            status = "error"
            raise
        finally:
            search_requests_total.add(1, {"status": status})
            search_stage_duration_ms.record(
                (perf_counter() - total_start) * 1000, {"stage": "total"}
            )
