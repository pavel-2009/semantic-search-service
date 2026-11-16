"""Rating rules: "рейтинг выше 7.5", "оценка 7-9", "8+", "высокий рейтинг"."""

import re

from src.services.search_service.parsing.filter_extractor.rules import (
    DASH,
    MAX_RATING,
    Rule,
    Values,
    const,
    number_group,
    rule,
)

HIGH_RATING = 7.0
LOW_RATING = 5.0

RATING_WORD = r"(?:рейтинг\w*|оценк\w*|оценен\w*|kp|кинопоиск\w*|imdb|имдб)"
RATING_PREFIX = rf"(?:(?:с|со|по)\s+)?{RATING_WORD}"
GTE_OPS = (
    r"не\s+ниже|не\s+меньше|не\s+менее|как\s+минимум|хотя\s+бы|минимум|"
    r"выше|больше|более|свыше|от|>=|>"
)
LTE_OPS = (
    r"не\s+выше|не\s+больше|не\s+более|как\s+максимум|максимум|"
    r"ниже|меньше|менее|до|<=|<"
)


def _rating(value: str) -> float | None:
    number = float(value.replace(",", "."))
    return number if 0 <= number <= MAX_RATING else None


def _range(m: re.Match[str], _: int) -> Values | None:
    low, high = _rating(m["a"]), _rating(m["b"])
    if low is None or high is None:
        return None
    return {"rating_gte": min(low, high), "rating_lte": max(low, high)}


def _gte(m: re.Match[str], _: int) -> Values | None:
    value = _rating(m["n"])
    return None if value is None else {"rating_gte": value}


def _bound(m: re.Match[str], _: int) -> Values | None:
    """Upper bound when the `lte` group matched, lower bound otherwise."""
    value = _rating(m["n"])
    if value is None:
        return None
    return {"rating_lte" if m["lte"] else "rating_gte": value}


RATING_RULES: list[Rule] = [
    # "рейтинг от 7 до 9", "оценка 7-9", "рейтинг между 6 и 8"
    rule(
        rf"{RATING_PREFIX}[\s:]*(?:от\s+|между\s+)?{number_group('a')}"
        rf"(?:{DASH}|\s+до\s+|\s+и\s+|\s+по\s+){number_group('b')}",
        _range,
    ),
    # "7 из 10", "оценка 8 из 10"
    rule(rf"(?:{RATING_WORD}[\s:]*)?{number_group('n')}\s+из\s+10(?!\d)", _gte),
    # "рейтинг 7+", "8+", "оценка 8 и выше", "5 и ниже"
    rule(
        rf"(?:{RATING_PREFIX}[\s:]*)?{number_group('n')}\s*"
        r"(?:\+|и\s+(?:выше|больше|более)|(?P<lte>и\s+(?:ниже|меньше|менее)))"
        rf"(?:\s+{RATING_WORD})?",
        _bound,
    ),
    # "рейтинг выше 7", "с рейтингом не ниже 7.5", "оценка до 5", "рейтинг 8"
    rule(
        rf"{RATING_PREFIX}[\s:=]*"
        rf"(?:(?P<lte>{LTE_OPS})\s*|(?:{GTE_OPS})\s*)?{number_group('n')}",
        _bound,
    ),
    # Qualitative phrases
    rule(
        r"(?:(?:высок|хорош)\w+\s+(?:рейтинг|оценк)\w*|высоко\s+оценен\w*)",
        const(rating_gte=HIGH_RATING),
    ),
    rule(
        r"(?:(?:низк|плох)\w+\s+(?:рейтинг|оценк)\w*|низко\s+оценен\w*)",
        const(rating_lte=LOW_RATING),
    ),
]
