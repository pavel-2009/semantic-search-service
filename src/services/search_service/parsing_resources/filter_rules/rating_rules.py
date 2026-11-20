"""Rating rules: "рейтинг выше 7.5", "оценка 7-9", "8+", "высокий рейтинг", negations."""

import re

from src.services.search_service.parsing_resources.filter_rules.rules import (
    AVOID_PREFIX,
    DASH,
    MAX_RATING,
    WB,
    WE,
    Rule,
    Values,
    const,
    number_group,
    rule,
)

HIGH_RATING = 7.0
AVOID_LOW_RATING = 6.0
LOW_RATING = 5.0

RATING_WORD = rf"{WB}(?:рейтинг\w*|оценк\w*|оценен\w*|kp|кинопоиск\w*|imdb|имдб)"
RATING_PREFIX = rf"{WB}(?:(?:с|со|по|на)\s+)?(?:рейтинг\w*|оценк\w*|оценен\w*|kp|кинопоиск\w*|imdb|имдб)"
GTE_OPS = (
    r"не\s+ниже|не\s+меньше|не\s+менее|как\s+минимум|хотя\s+бы|минимум|"
    r"выше|больше|более|свыше|от|>=|>"
)
LTE_OPS = (
    r"не\s+выше|не\s+больше|не\s+более|как\s+максимум|максимум|"
    r"ниже|меньше|менее|до|<=|<"
)

_HIGH_RATING_PHRASE = (
    r"(?:(?:высок|хорош|отличн|неплох|достойн|топов|лучш)\w*\s+(?:рейтинг|оценк)\w*"
    r"|высоко\s*оценен\w*)"
)
_LOW_RATING_PHRASE = (
    r"(?:(?:низк|плох|слаб)\w*\s+(?:рейтинг|оценк)\w*"
    r"|низко\s*оценен\w*)"
)
_POS_REVIEW_PHRASE = r"(?:хорош|положительн|отличн|высок|позитивн)\w*\s+(?:отзыв|рецензи)\w*"
_NEG_REVIEW_PHRASE = r"(?:плох|негативн|отрицательн|низк|слаб)\w*\s+(?:отзыв|рецензи)\w*"


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


def _avoid_bound(m: re.Match[str], _: int) -> Values | None:
    """Negated explicit bound: avoiding 'below N' implies >= N; avoiding 'above N' skips filter."""
    value = _rating(m["n"])
    if value is None:
        return None
    return {"rating_gte": value} if m["lte"] else {}


RATING_RULES: list[Rule] = [
    # "рейтинг от 7 до 9", "оценка 7-9", "рейтинг между 6 и 8"
    rule(
        rf"{RATING_PREFIX}[\s:]*(?:от\s+|между\s+)?{number_group('a')}"
        rf"(?:{DASH}|\s+до\s+|\s+и\s+|\s+по\s+){number_group('b')}",
        _range,
    ),
    # "7 из 10", "оценка 8 из 10"
    rule(rf"(?:{RATING_WORD}[\s:]*)?{number_group('n')}\s+из\s+10(?!\d)", _gte),
    # "рейтинг 7+", "8+", "оценка 8 и выше", "5 и ниже", "8 и больше"
    rule(
        rf"(?:{RATING_PREFIX}[\s:]*)?{number_group('n')}\s*"
        r"(?:\+|и\s+(?:выше|больше|более)|(?P<lte>и\s+(?:ниже|меньше|менее)))"
        rf"(?:\s+{RATING_WORD})?",
        _bound,
    ),
    # Negated explicit bound: "избегай фильмов с рейтингом ниже 6"
    rule(
        rf"{AVOID_PREFIX}(?:рейтинг\w*|оценк\w*)[\s:=]*"
        rf"(?:(?P<lte>{LTE_OPS})|(?:{GTE_OPS}))\s*{number_group('n')}",
        _avoid_bound,
    ),
    # "рейтинг выше 7", "с рейтингом не ниже 7.5", "оценка до 5", "рейтинг 8"
    rule(
        rf"{RATING_PREFIX}[\s:=]*"
        rf"(?:(?P<lte>{LTE_OPS})\s*|(?:{GTE_OPS})\s*)?{number_group('n')}",
        _bound,
    ),
    # Negated high rating: "без высокого рейтинга", "не обязательно с высоким рейтингом"
    rule(
        rf"{AVOID_PREFIX}{_HIGH_RATING_PHRASE}"
        rf"(?:\s+(?:и|,)\s+{_POS_REVIEW_PHRASE})?{WE}",
        const(),
    ),
    # Qualitative high rating (+ optional positive reviews)
    rule(
        rf"{WB}(?:(?:с|со)\s+)?{_HIGH_RATING_PHRASE}"
        rf"(?:\s+(?:и|,)\s+(?:с\s+)?{_POS_REVIEW_PHRASE})?{WE}",
        const(rating_gte=HIGH_RATING),
    ),
    # Negated low rating / negative reviews: "избегай фильмов с низким рейтингом и негативными отзывами"
    rule(
        rf"{AVOID_PREFIX}(?:{_LOW_RATING_PHRASE}|{_NEG_REVIEW_PHRASE})"
        rf"(?:\s+(?:и|,)\s+(?:{_LOW_RATING_PHRASE}|{_NEG_REVIEW_PHRASE}))*{WE}",
        const(rating_gte=AVOID_LOW_RATING),
    ),
    # Standalone positive reviews
    rule(
        rf"{WB}(?:(?:с|со)\s+)?{_POS_REVIEW_PHRASE}{WE}",
        const(rating_gte=HIGH_RATING),
    ),
    # Qualitative low rating (+ optional negative reviews)
    rule(
        rf"{WB}(?:(?:с|со)\s+)?{_LOW_RATING_PHRASE}"
        rf"(?:\s+(?:и|,)\s+(?:с\s+)?{_NEG_REVIEW_PHRASE})?{WE}",
        const(rating_lte=LOW_RATING),
    ),
    # Standalone negative reviews
    rule(
        rf"{WB}(?:(?:с|со)\s+)?{_NEG_REVIEW_PHRASE}{WE}",
        const(rating_lte=LOW_RATING),
    ),
]
