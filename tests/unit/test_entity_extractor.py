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


def test_extracts_quoted_and_unquoted_movie_titles() -> None:
    quoted = extractor.extract('похожие на "Интерстеллар" и «Гравитацию» про космос')
    assert quoted.entities == "Интерстеллар. Гравитация"
    assert quoted.text == "похожие на и про космос"

    unquoted = extractor.extract("похожие на Матрицу и Начало про виртуальную реальность")
    assert unquoted.entities == "Матрица. Начало"
    assert unquoted.text == "похожие на и про виртуальную реальность"


def test_extracts_multiword_sci_fi_and_ignores_negated_genres() -> None:
    sci_fi = extractor.extract("фильмы с элементами научной фантастики")
    assert sci_fi.entities == "фантастика"
    assert sci_fi.text == "фильмы с элементами"

    negated = extractor.extract("без ужасов и комедий, триллер Дени Вильнева")
    assert negated.entities == "триллер. Дени Вильнев"
    assert negated.text == "без и"


def test_strict_horror_genre_does_not_match_singular_exclaim() -> None:
    assert extractor.extract("какой ужас творится в городе").entities is None
