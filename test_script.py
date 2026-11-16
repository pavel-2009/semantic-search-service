"""Test script for on-hand testing components."""

from src.services.indexer.embedder import MovieEmbedder
from src.services.search_service.parsing.text_parser import TextParser


movie_request = """
    Посоветуй интересные фильмы про космос, которые похожи на "Интерстеллар" и "Гравитацию".
"""

parsed_text = TextParser.parse(movie_request)

print("Parsed Text:", parsed_text)
