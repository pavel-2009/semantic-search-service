"""Tests for VibeExtractor and the mood dictionary."""

from collections import Counter

from core.vibe import format_vibe
from services.search_service.parsing.mood_dictionary import MOOD_TAGS
from services.search_service.parsing.vibe_extractor import ExtractedVibe, VibeExtractor

extractor = VibeExtractor()


def test_moods_in_order_of_appearance() -> None:
    result = extractor.extract("мрачный фильм про петлю времени, чтобы было жутко")
    assert result.moods == ["мрачный", "жуткий"]
    assert result.vibe == "Мрачный, жуткий."


def test_inflected_forms_yo_and_phrases() -> None:
    assert extractor.extract("уютное кино на тёплый вечер").moods == ["уютный"]
    assert extractor.extract("хочу поплакать").moods == ["грустный"]
    assert extractor.extract("что-нибудь с чёрным юмором").moods == ["остроумный"]
    assert extractor.extract("мрачные и тяжелые драмы").moods == ["мрачный", "тяжёлый"]


def test_duplicates_are_collapsed() -> None:
    assert extractor.extract("мрачный, мрачная, мрачное").moods == ["мрачный"]


def test_no_mood_gives_empty_vibe() -> None:
    assert extractor.extract("фильм про Ивана") == ExtractedVibe()


def test_plot_words_are_not_moods() -> None:
    assert extractor.extract("фильм про войну и космос в 1990-х").moods == []


def test_vibe_format() -> None:
    assert format_vibe(["мрачный", "жуткий", "мрачный"]) == "Мрачный, жуткий."
    assert format_vibe([]) is None


def test_every_trigger_belongs_to_one_tag() -> None:
    counts = Counter(
        trigger.lower().replace("ё", "е")
        for triggers in MOOD_TAGS.values()
        for trigger in triggers
    )
    assert [trigger for trigger, count in counts.items() if count > 1] == []
