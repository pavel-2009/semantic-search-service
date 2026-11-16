"""Expressions and lookup sets used for entity extraction."""

import re

from src.services.search_service.parsing_resources.dictionaries import GENRE_TAGS, STOP_WORDS
from src.services.search_service.parsing_resources.mood_dictionary import MOOD_TAGS

CYRILLIC_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"

QUOTED_TITLE_RE = re.compile(
    r"«([^»\n]{2,80})»"
    r"|„([^“\"\n]{2,80})[“\"]"
    r"|\"([^\"\n]{2,80})\""
    r"|(?<![а-яёa-z0-9])'([^'\n]{2,80})'(?![а-яёa-z0-9])"
)
SIMILARITY_TRIGGER_RE = re.compile(
    r"(?<![а-яёa-z0-9])(?:похож\w*\s+(?:на|с)|в\s+духе|наподобие|вроде|типа|"
    r"такие\s+как|такой\s+как|как|аналог\w*|названи\w*(?:\s+которого)?)\s+",
    re.IGNORECASE,
)
NEGATED_GENRE_RE = re.compile(
    r"(?:^|[.,;!?]\s*|\s)"
    r"(?:без|кроме|исключая|помимо|избега\w*|никак\w*|только\s+не|не)"
    r"(?:\s+(?:таких\s+жанр\w*\s+как|жанр\w*|фильм\w*))?"
    r"\s*(?:[а-яё-]+\s*(?:и|или)\s*)*$",
    re.IGNORECASE,
)
TITLE_CONNECTORS = frozenset(
    {"по", "из", "в", "во", "на", "с", "со", "к", "о", "об", "у", "для", "от", "под", "над"}
)
LIST_SEPARATORS_RE = re.compile(r"^\s*(?:,|и|или)\s+", re.IGNORECASE)
TOKEN_SPAN_RE = re.compile(r"[а-яёa-z0-9-]+", re.IGNORECASE)
HAS_LETTER_RE = re.compile(r"[а-яёa-z]", re.IGNORECASE)

NON_ENTITY_LEMMAS = frozenset(
    {word.lower().replace("ё", "е") for word in STOP_WORDS}
    | {
        trigger.lower().replace("ё", "е")
        for triggers in (*GENRE_TAGS.values(), *MOOD_TAGS.values())
        for trigger in triggers
    }
)
