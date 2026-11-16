"""Tests for VibeExtractor and the mood dictionary."""

from collections import Counter

from src.core.vibe import format_vibe
from src.services.search_service.parsing_resources.mood_dictionary import MOOD_TAGS
from src.services.search_service.parsing.vibe_extractor import ExtractedVibe, VibeExtractor

extractor = VibeExtractor()


def test_moods_are_extracted_and_removed_from_text() -> None:
    result = extractor.extract("мрачный фильм про петлю времени, чтобы было жутко")
    assert result.vibe == "Мрачный, жуткий."
    assert result.text == "фильм про петлю времени, чтобы было"


def test_inflected_forms_yo_and_phrases() -> None:
    assert extractor.extract("уютное кино на тёплый вечер").vibe == "Уютный."
    assert extractor.extract("хочу поплакать").vibe == "Грустный."
    assert extractor.extract("что-нибудь с чёрным юмором").vibe == "Остроумный."
    assert extractor.extract("мрачные и тяжелые драмы").vibe == "Мрачный, тяжёлый."


def test_duplicates_are_collapsed() -> None:
    assert extractor.extract("мрачный, мрачная, мрачное").vibe == "Мрачный."


def test_no_mood_keeps_text() -> None:
    assert extractor.extract("фильм про Ивана") == ExtractedVibe(text="фильм про Ивана")


def test_plot_words_are_not_moods() -> None:
    assert extractor.extract("фильм про войну и космос в 1990-х").vibe is None


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


def test_participle_moods_and_think_phrases_are_inflected() -> None:
    res = extractor.extract("захватывающая атмосфера с захватывающим духом, заставляют задуматься")
    assert res.vibe == "Динамичный, атмосферный, философский."
    assert "захватывающая" not in res.text
    assert "захватывающим" not in res.text
    assert "задуматься" not in res.text
