"""Tests for EntityExtractor."""

from src.services.search_service.parsing.entity_extraction import (
     EntityExtractor,
    ExtractedEntities,
)

extractor = EntityExtractor()


def test_extracts_persons_and_genres() -> None:
    result = extractor.extract("триллер Кристофера Нолана с Леонардо Ди Каприо про сны")
    assert result.entities == "триллер. Кристофер Нолан. Леонардо Ди Каприо"
    assert result.text == "с про сны"


def test_extracts_inflected_genres() -> None:
    result = extractor.extract("исторические комедии и документальные фильмы")
    assert result.entities == "история. комедия. документальный"
    assert result.text == "и фильмы"


def test_no_entities_keeps_text() -> None:
    assert extractor.extract("фильм про ограбление") == ExtractedEntities(
        text="фильм про ограбление"
    )
