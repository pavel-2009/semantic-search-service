"""Tests for VibeExtractor."""

from services.search_service.parsing.vibe_extractor import ExtractedVibe, VibeExtractor

extractor = VibeExtractor()


def test_vibe_is_built_and_removed_from_text() -> None:
    result = extractor.extract("мрачный триллер про космос, французский", decades=["1990-е"])
    assert result.vibe == (
        "Жанры: триллер. Атмосфера и теги: мрачный, космос. "
        "Страна и эпоха: Франция, 1990-е."
    )
    assert result.text == "про"


def test_inflected_forms_and_yo() -> None:
    result = extractor.extract("добрые комедии про дружбу и тяжелое детство")
    assert result.vibe is not None
    assert "комедия" in result.vibe and "дружба" in result.vibe and "мрачный" in result.vibe
    assert result.text == "про и детство"


def test_no_vibe_keeps_text() -> None:
    assert extractor.extract("фильм про Ивана") == ExtractedVibe(text="фильм про Ивана")
