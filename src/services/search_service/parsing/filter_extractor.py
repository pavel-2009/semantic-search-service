"""Keywords, filters and limits extraction.

Extracts year and rating constraints from a free-form Russian query and returns
the query text with the matched phrases removed.

Examples:
    "фильмы 90-х с рейтингом выше 7.5"  -> 1990..1999, rating >= 7.5
    "комедии после 2010 года"            -> year >= 2011
    "триллер с 2005 по 2015"             -> 2005..2015
    "что-нибудь свежее, оценка 8+"       -> year >= current-4, rating >= 8
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

MIN_YEAR = 1900
MAX_YEAR = 2030
MAX_RATING = 10.0

RECENT_YEARS = 5  # "свежее", "новинки" -> last N years
OLD_BEFORE_YEAR = 1990  # "старое", "классика" -> before this year
HIGH_RATING = 7.0  # "высокий рейтинг"
LOW_RATING = 5.0  # "низкий рейтинг"

NUMBER_WORDS = {
    "один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5,
    "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
}

# Decade stems (text is lowercased, "ё" -> "е").
DECADE_WORDS = {
    "двадцат": 1920, "тридцат": 1930, "сороков": 1940, "пятидесят": 1950,
    "шестидесят": 1960, "семидесят": 1970, "восьмидесят": 1980,
    "девяност": 1990, "нулев": 2000, "десят": 2010,
}
# Part of a decade -> (offset from decade start, offset to decade end).
DECADE_PARTS = {"начал": (0, 3), "середин": (4, 6), "кон": (7, 9)}


# --------------------------------------------------------------------------- #
# Regex building blocks
# --------------------------------------------------------------------------- #


def _year(name: str) -> str:
    return rf"(?<!\d)(?P<{name}>(?:19|20)\d{{2}})(?!\d)"


def _num(name: str) -> str:
    return rf"(?<![\d.,])(?P<{name}>\d{{1,2}}(?:[.,]\d{{1,2}})?)(?!\d)"


YEAR_SUFFIX = r"(?:\s*(?:годов|года|году|год|г\b\.?))?"
DASH = r"\s*[-–—]\s*"

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

DECADE_PART_RE = r"(?:(?P<part>начал|середин|кон)\w*\s+(?:\d{0,4}\s*)?)?"
_NUMBER_WORD_RE = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
_DECADE_WORD_RE = "|".join(rf"{stem}(?:ые|ых|ым|ыми)" for stem in DECADE_WORDS)


# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #


@dataclass
class FilterResult:
    """Extracted filters plus the query text without the matched phrases."""

    year_gte: int | None = None
    year_lte: int | None = None
    rating_gte: float | None = None
    rating_lte: float | None = None
    text: str = ""


Values = dict[str, int | float]
Handler = Callable[[re.Match[str], int], Values | None]


@dataclass(frozen=True)
class Rule:
    """A regex plus a handler returning the filters it produces (None = skip)."""

    name: str
    pattern: re.Pattern[str]
    handler: Handler


def _rule(name: str, pattern: str, handler: Handler) -> Rule:
    return Rule(name, re.compile(pattern, re.IGNORECASE), handler)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def is_year(value: str | int) -> bool:
    """Return True if value looks like a plausible movie year."""
    text = str(value)
    return text.isdigit() and MIN_YEAR <= int(text) <= MAX_YEAR


def _rating(value: str) -> float | None:
    number = float(value.replace(",", "."))
    return number if 0 <= number <= MAX_RATING else None


def _years(low: int, high: int) -> Values | None:
    if not (is_year(low) and is_year(high)):
        return None
    return {"year_gte": min(low, high), "year_lte": max(low, high)}


def _const(**values: int | float) -> Handler:
    return lambda _m, _c: dict(values)


def _decade(start: int, part: str | None) -> Values | None:
    low, high = start, start + 9
    if part:
        offset_low, offset_high = DECADE_PARTS[part]
        low, high = start + offset_low, start + offset_high
    return _years(low, min(high, MAX_YEAR))


# --------------------------------------------------------------------------- #
# Rating handlers
# --------------------------------------------------------------------------- #


def _rating_range(m: re.Match[str], _: int) -> Values | None:
    low, high = _rating(m["a"]), _rating(m["b"])
    if low is None or high is None:
        return None
    return {"rating_gte": min(low, high), "rating_lte": max(low, high)}


def _rating_gte(m: re.Match[str], _: int) -> Values | None:
    value = _rating(m["n"])
    return None if value is None else {"rating_gte": value}


def _rating_op(m: re.Match[str], _: int) -> Values | None:
    value = _rating(m["n"])
    if value is None:
        return None
    return {"rating_lte" if m["lte"] else "rating_gte": value}


def _rating_trailing(m: re.Match[str], _: int) -> Values | None:
    value = _rating(m["n"])
    if value is None:
        return None
    return {"rating_lte" if m["lte"] else "rating_gte": value}


RATING_RULES: list[Rule] = [
    # "рейтинг от 7 до 9", "оценка 7-9", "рейтинг между 6 и 8"
    _rule(
        "rating_range",
        rf"{RATING_PREFIX}[\s:]*(?:от\s+|между\s+)?{_num('a')}"
        rf"(?:{DASH}|\s+до\s+|\s+и\s+|\s+по\s+){_num('b')}",
        _rating_range,
    ),
    # "7 из 10", "оценка 8 из 10"
    _rule(
        "rating_out_of_ten",
        rf"(?:{RATING_WORD}[\s:]*)?{_num('n')}\s+из\s+10(?!\d)",
        _rating_gte,
    ),
    # "рейтинг 7+", "8+", "оценка 8 и выше", "5 и ниже"
    _rule(
        "rating_trailing",
        rf"(?:{RATING_PREFIX}[\s:]*)?{_num('n')}\s*"
        r"(?:\+|и\s+(?:выше|больше|более)|(?P<lte>и\s+(?:ниже|меньше|менее)))"
        rf"(?:\s+{RATING_WORD})?",
        _rating_trailing,
    ),
    # "рейтинг выше 7", "с рейтингом не ниже 7.5", "оценка до 5", "рейтинг 8"
    _rule(
        "rating_operator",
        rf"{RATING_PREFIX}[\s:=]*"
        rf"(?:(?P<lte>{LTE_OPS})\s*|(?:{GTE_OPS})\s*)?{_num('n')}",
        _rating_op,
    ),
    # Qualitative phrases
    _rule(
        "rating_high",
        r"(?:(?:высок|хорош)\w+\s+(?:рейтинг|оценк)\w*|высоко\s+оценен\w*)",
        _const(rating_gte=HIGH_RATING),
    ),
    _rule(
        "rating_low",
        r"(?:(?:низк|плох)\w+\s+(?:рейтинг|оценк)\w*|низко\s+оценен\w*)",
        _const(rating_lte=LOW_RATING),
    ),
]


# --------------------------------------------------------------------------- #
# Year handlers
# --------------------------------------------------------------------------- #


def _y(m: re.Match[str], group: str = "y") -> int:
    return int(m[group])


def _year_range(m: re.Match[str], _: int) -> Values | None:
    return _years(_y(m, "a"), _y(m, "b"))


def _decade_numeric(m: re.Match[str], _: int) -> Values | None:
    raw = m["d"]
    if len(raw) == 4:
        start = int(raw)
    else:
        number = int(raw)
        start = 1900 + number if number >= 30 else 2000 + number
    if not is_year(start):
        return None
    return _decade(start, m["part"])


def _decade_word(m: re.Match[str], _: int) -> Values | None:
    word = m["w"]
    stem = next(s for s in DECADE_WORDS if word.startswith(s))
    return _decade(DECADE_WORDS[stem], m["part"])


def _last_years(m: re.Match[str], current: int) -> Values | None:
    raw = m["n"]
    count = int(raw) if raw.isdigit() else NUMBER_WORDS.get(raw)
    if not count:
        return None
    return {"year_gte": current - count + 1}


def _year_gte(m: re.Match[str], _: int) -> Values | None:
    return {"year_gte": _y(m)} if is_year(_y(m)) else None


def _year_after(m: re.Match[str], _: int) -> Values | None:
    year = _y(m) + 1
    return {"year_gte": year} if is_year(year) else None


def _year_lte(m: re.Match[str], _: int) -> Values | None:
    return {"year_lte": _y(m)} if is_year(_y(m)) else None


def _year_before(m: re.Match[str], _: int) -> Values | None:
    """'до 2010' excludes 2010, 'до 2010 включительно' includes it."""
    year = _y(m) if m["incl"] else _y(m) - 1
    return {"year_lte": year} if is_year(year) else None


def _year_exact(m: re.Match[str], _: int) -> Values | None:
    return _years(_y(m), _y(m))


def _relative_year(offset: int) -> Handler:
    def handler(_m: re.Match[str], current: int) -> Values:
        return {"year_gte": current - offset, "year_lte": current - offset}

    return handler


def _recent(_m: re.Match[str], current: int) -> Values:
    return {"year_gte": current - RECENT_YEARS + 1}


YEAR_RULES: list[Rule] = [
    # "с 2010 по 2020", "от 2010 до 2020", "между 2010 и 2020"
    _rule(
        "year_range_words",
        rf"(?:с|от|между)\s+{_year('a')}{YEAR_SUFFIX}\s+(?:по|до|и)\s+"
        rf"{_year('b')}{YEAR_SUFFIX}(?:\s+включительно)?",
        _year_range,
    ),
    # "2010-2020", "в 2010–2020 годах"
    _rule(
        "year_range_dash",
        rf"(?:в\s+)?{_year('a')}{DASH}{_year('b')}{YEAR_SUFFIX}",
        _year_range,
    ),
    # Decades: "90-х", "80е", "2000-х", "начало 2000-х", "конец 90-х"
    _rule(
        "decade_numeric",
        rf"(?:в\s+)?{DECADE_PART_RE}(?<!\d)(?P<d>(?:19|20)?\d0)\s*-?\s*"
        r"(?:х|е|ые|ых|ми)(?:\s+годы|\s+годов|\s+года)?(?![а-я])",
        _decade_numeric,
    ),
    # "восьмидесятые", "в девяностых", "нулевые"
    _rule(
        "decade_word",
        rf"(?:в\s+)?{DECADE_PART_RE}(?P<w>{_DECADE_WORD_RE})(?:\s+годы|\s+годов|\s+года)?",
        _decade_word,
    ),
    # "последние 5 лет", "за последние три года"
    _rule(
        "last_years",
        rf"(?:за\s+)?последни[еих]\s+(?P<n>\d{{1,2}}|{_NUMBER_WORD_RE})\s+(?:лет|года|год)",
        _last_years,
    ),
    # Relative years
    _rule("year_this", r"(?:в\s+)?(?:этом|текущем)\s+году|этого\s+года", _relative_year(0)),
    _rule("year_last", r"(?:в\s+)?прошлом\s+году|прошлого\s+года", _relative_year(1)),
    _rule(
        "year_before_last",
        r"(?:в\s+)?позапрошлом\s+году|позапрошлого\s+года",
        _relative_year(2),
    ),
    # Qualitative recency / age
    _rule(
        "year_recent",
        r"(?:свеж\w+|недавн\w+|современн\w+|новинк\w+)",
        _recent,
    ),
    _rule(
        "year_old",
        r"(?:старые|старое|старый|старых|классик\w*|ретро)",
        _const(year_lte=OLD_BEFORE_YEAR - 1),
    ),
    # "2010 и позже", "с 2010 года и новее"
    _rule(
        "year_trailing_gte",
        rf"(?:(?:с|от)\s+)?{_year('y')}{YEAR_SUFFIX}\s+и\s+(?:позже|позднее|новее|свежее)",
        _year_gte,
    ),
    # "1999 и раньше", "до 1999 и старше"
    _rule(
        "year_trailing_lte",
        rf"(?:(?:до|по)\s+)?{_year('y')}{YEAR_SUFFIX}\s+и\s+(?:раньше|ранее|старше)",
        _year_lte,
    ),
    # "не позже 2010", "по 2010", "вплоть до 2010" (before year_after: "не позже")
    _rule(
        "year_upto_inclusive",
        rf"(?:не\s+позже|не\s+позднее|по|вплоть\s+до)\s+{_year('y')}{YEAR_SUFFIX}",
        _year_lte,
    ),
    # "после 2010", "позже 2010", "новее 2010"
    _rule(
        "year_after",
        rf"(?:после|позже|позднее|новее|свежее)\s+{_year('y')}{YEAR_SUFFIX}",
        _year_after,
    ),
    # "с 2010", "от 2010", "начиная с 2010", "не раньше 2010"
    _rule(
        "year_since",
        rf"(?:начиная\s+с|не\s+раньше|не\s+ранее|с|от)\s+{_year('y')}{YEAR_SUFFIX}",
        _year_gte,
    ),
    # "до 2010", "раньше 2010", "старше 2010", "до 2010 включительно"
    _rule(
        "year_before",
        rf"(?:до|раньше|ранее|старше)\s+{_year('y')}{YEAR_SUFFIX}(?P<incl>\s+включительно)?",
        _year_before,
    ),
    # Exact year: "2014", "в 2014 году", "2014 г."
    _rule(
        "year_exact",
        rf"(?:(?:в|за|из)\s+)?{_year('y')}{YEAR_SUFFIX}",
        _year_exact,
    ),
]

RULES: list[Rule] = [*RATING_RULES, *YEAR_RULES]


# --------------------------------------------------------------------------- #
# Extractor
# --------------------------------------------------------------------------- #


class FilterExtractor:
    """Extract year and rating filters from a query.

    Rules are applied in order; the first rule that sets a field wins. Every
    matched phrase is removed from the returned text.
    """

    def __init__(
        self,
        rules: list[Rule] | None = None,
        current_year: int | None = None,
    ) -> None:
        self.rules = rules if rules is not None else RULES
        self.current_year = current_year

    def extract(self, text: str) -> FilterResult:
        """Return filters found in text and the text with those phrases removed."""
        current = self.current_year or date.today().year
        working = text.lower().replace("ё", "е")
        result = FilterResult()

        for rule in self.rules:
            working = rule.pattern.sub(
                lambda m, rule=rule: self._apply(rule, m, current, result),
                working,
            )

        result.text = self._clean(working)
        return result

    @staticmethod
    def _apply(rule: Rule, match: re.Match[str], current: int, result: FilterResult) -> str:
        values = rule.handler(match, current)
        if values is None:
            return match.group(0)
        for field, value in values.items():
            if getattr(result, field) is None:
                setattr(result, field, value)
        return " "

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"(?:^|\s)[,.;:\-–—]+(?=\s|$)", " ", text)
        return " ".join(text.split()).strip(" ,.;:-")
