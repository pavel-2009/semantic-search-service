"""Year rules: "с 2005 по 2015", "90-х", "после 2010", "последние 5 лет", "свежее"."""

import re

from src.services.search_service.parsing.filter_extractor.rules import (
    DASH,
    MAX_YEAR,
    Handler,
    Rule,
    Values,
    const,
    is_year,
    rule,
    year_group,
)

RECENT_YEARS = 5  # "свежее", "новинки" -> last N years
OLD_BEFORE_YEAR = 1990  # "старое", "классика" -> before this year

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

YEAR_SUFFIX = r"(?:\s*(?:годов|года|году|год|г\b\.?))?"
DECADE_SUFFIX = r"(?:\s+годы|\s+годов|\s+года)?"
DECADE_PART = r"(?:(?P<part>начал|середин|кон)\w*\s+(?:\d{0,4}\s*)?)?"
NUMBER_WORD = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
DECADE_WORD = "|".join(rf"{stem}(?:ые|ых|ым|ыми)" for stem in DECADE_WORDS)


def _years(low: int, high: int) -> Values | None:
    if not (is_year(low) and is_year(high)):
        return None
    return {"year_gte": min(low, high), "year_lte": max(low, high)}


def _decade(start: int, part: str | None) -> Values | None:
    low, high = start, start + 9
    if part:
        offset_low, offset_high = DECADE_PARTS[part]
        low, high = start + offset_low, start + offset_high
    return _years(low, min(high, MAX_YEAR))


def _range(m: re.Match[str], _: int) -> Values | None:
    return _years(int(m["a"]), int(m["b"]))


def _exact(m: re.Match[str], _: int) -> Values | None:
    return _years(int(m["y"]), int(m["y"]))


def _decade_numeric(m: re.Match[str], _: int) -> Values | None:
    raw = m["d"]
    if len(raw) == 4:
        start = int(raw)
    else:
        number = int(raw)
        start = 1900 + number if number >= 30 else 2000 + number
    return _decade(start, m["part"]) if is_year(start) else None


def _decade_word(m: re.Match[str], _: int) -> Values | None:
    stem = next(s for s in DECADE_WORDS if m["w"].startswith(s))
    return _decade(DECADE_WORDS[stem], m["part"])


def _last_years(m: re.Match[str], current: int) -> Values | None:
    raw = m["n"]
    count = int(raw) if raw.isdigit() else NUMBER_WORDS.get(raw)
    return {"year_gte": current - count + 1} if count else None


def _gte(shift: int = 0) -> Handler:
    """Lower bound: the matched year plus `shift`."""

    def handler(m: re.Match[str], _: int) -> Values | None:
        year = int(m["y"]) + shift
        return {"year_gte": year} if is_year(year) else None

    return handler


def _lte(shift: int = 0) -> Handler:
    """Upper bound: the matched year plus `shift`."""

    def handler(m: re.Match[str], _: int) -> Values | None:
        year = int(m["y"]) + shift
        return {"year_lte": year} if is_year(year) else None

    return handler


def _before(m: re.Match[str], _: int) -> Values | None:
    """'до 2010' excludes 2010, 'до 2010 включительно' includes it."""
    year = int(m["y"]) - (0 if m["incl"] else 1)
    return {"year_lte": year} if is_year(year) else None


def _relative(offset: int) -> Handler:
    """The year `offset` years before the current one."""

    def handler(_m: re.Match[str], current: int) -> Values:
        return {"year_gte": current - offset, "year_lte": current - offset}

    return handler


def _recent(_m: re.Match[str], current: int) -> Values:
    return {"year_gte": current - RECENT_YEARS + 1}


YEAR_RULES: list[Rule] = [
    # "с 2010 по 2020", "от 2010 до 2020", "между 2010 и 2020"
    rule(
        rf"(?:с|от|между)\s+{year_group('a')}{YEAR_SUFFIX}\s+(?:по|до|и)\s+"
        rf"{year_group('b')}{YEAR_SUFFIX}(?:\s+включительно)?",
        _range,
    ),
    # "2010-2020", "в 2010–2020 годах"
    rule(rf"(?:в\s+)?{year_group('a')}{DASH}{year_group('b')}{YEAR_SUFFIX}", _range),
    # Decades: "90-х", "80е", "2000-х", "начало 2000-х", "конец 90-х"
    rule(
        rf"(?:в\s+)?{DECADE_PART}(?<!\d)(?P<d>(?:19|20)?\d0)\s*-?\s*"
        rf"(?:х|е|ые|ых|ми){DECADE_SUFFIX}(?![а-я])",
        _decade_numeric,
    ),
    # "восьмидесятые", "в девяностых", "нулевые"
    rule(rf"(?:в\s+)?{DECADE_PART}(?P<w>{DECADE_WORD}){DECADE_SUFFIX}", _decade_word),
    # "последние 5 лет", "за последние три года"
    rule(
        rf"(?:за\s+)?последни[еих]\s+(?P<n>\d{{1,2}}|{NUMBER_WORD})\s+(?:лет|года|год)",
        _last_years,
    ),
    # Relative years
    rule(r"(?:в\s+)?(?:этом|текущем)\s+году|этого\s+года", _relative(0)),
    rule(r"(?:в\s+)?прошлом\s+году|прошлого\s+года", _relative(1)),
    rule(r"(?:в\s+)?позапрошлом\s+году|позапрошлого\s+года", _relative(2)),
    # Qualitative recency / age
    rule(r"(?:свеж\w+|недавн\w+|современн\w+|новинк\w+)", _recent),
    rule(
        r"(?:старые|старое|старый|старых|классик\w*|ретро)",
        const(year_lte=OLD_BEFORE_YEAR - 1),
    ),
    # "2010 и позже", "с 2010 года и новее"
    rule(
        rf"(?:(?:с|от)\s+)?{year_group('y')}{YEAR_SUFFIX}\s+и\s+(?:позже|позднее|новее|свежее)",
        _gte(),
    ),
    # "1999 и раньше", "до 1999 и старше"
    rule(
        rf"(?:(?:до|по)\s+)?{year_group('y')}{YEAR_SUFFIX}\s+и\s+(?:раньше|ранее|старше)",
        _lte(),
    ),
    # "не позже 2010", "по 2010", "вплоть до 2010" (before "после": "не позже")
    rule(
        rf"(?:не\s+позже|не\s+позднее|по|вплоть\s+до)\s+{year_group('y')}{YEAR_SUFFIX}",
        _lte(),
    ),
    # "после 2010", "позже 2010", "новее 2010"
    rule(
        rf"(?:после|позже|позднее|новее|свежее)\s+{year_group('y')}{YEAR_SUFFIX}",
        _gte(1),
    ),
    # "с 2010", "от 2010", "начиная с 2010", "не раньше 2010"
    rule(
        rf"(?:начиная\s+с|не\s+раньше|не\s+ранее|с|от)\s+{year_group('y')}{YEAR_SUFFIX}",
        _gte(),
    ),
    # "до 2010", "раньше 2010", "старше 2010", "до 2010 включительно"
    rule(
        rf"(?:до|раньше|ранее|старше)\s+{year_group('y')}{YEAR_SUFFIX}(?P<incl>\s+включительно)?",
        _before,
    ),
    # Exact year: "2014", "в 2014 году", "2014 г."
    rule(rf"(?:(?:в|за|из)\s+)?{year_group('y')}{YEAR_SUFFIX}", _exact),
]
