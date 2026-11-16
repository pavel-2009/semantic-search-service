"""Year rules: "с 2005 по 2015", "90-х", "годов 90-х и позже", "после 2010", "последние 5 лет", "свежее"."""

import re

from src.services.search_service.parsing_resources.filter_rules.rules import (
    AVOID_PREFIX,
    DASH,
    MAX_YEAR,
    WB,
    WE,
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
    "пару": 2, "пара": 2,
}

# Decade stems (text is lowercased, "ё" -> "е").
DECADE_WORDS = {
    "двадцат": 1920, "тридцат": 1930, "сороков": 1940, "пятидесят": 1950,
    "шестидесят": 1960, "семидесят": 1970, "восьмидесят": 1980,
    "девяност": 1990, "нулев": 2000, "двухтысячн": 2000, "десят": 2010,
}
# Part of a decade -> (offset from decade start, offset to decade end).
DECADE_PARTS = {"начал": (0, 3), "середин": (4, 6), "кон": (7, 9)}

YEAR_SUFFIX = rf"(?:\s*(?:годов|года|году|год|гг|г)(?!\w)\.?)?"
DECADE_SUFFIX = rf"(?:\s+(?:годы|годов|года|гг|г)(?!\w)\.?)?"
NUMBER_WORD = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
DECADE_WORD = "|".join(rf"{stem}(?:ые|ых|ым|ыми)" for stem in sorted(DECADE_WORDS, key=len, reverse=True))


def _decade_expr(prefix: str) -> str:
    """Build a named-group regex matching numeric or word decades, e.g. 'годов 90-х', 'восьмидесятые'."""
    part = rf"(?:(?P<{prefix}_part>начал|середин|кон)\w*\s+)?"
    numeric = rf"(?<!\d)(?P<{prefix}_d>(?:19|20)?\d0)\s*-?\s*(?:х|е|ые|ых|ым|ыми){WE}"
    word = rf"(?P<{prefix}_w>{DECADE_WORD}){WE}"
    return rf"(?:годов\s+)?{part}(?:{numeric}|{word}){DECADE_SUFFIX}"


def _decade_bounds(m: re.Match[str], prefix: str) -> tuple[int, int] | None:
    """Resolve a matched decade expression into an inclusive (low, high) year pair."""
    raw_d = m[f"{prefix}_d"]
    if raw_d is not None:
        if len(raw_d) == 4:
            start = int(raw_d)
        else:
            number = int(raw_d)
            start = 1900 + number if number >= 30 else 2000 + number
        if not is_year(start):
            return None
    else:
        word = m[f"{prefix}_w"]
        stem = next(s for s in DECADE_WORDS if word.startswith(s))
        start = DECADE_WORDS[stem]

    low, high = start, start + 9
    part = m[f"{prefix}_part"]
    if part:
        offset_low, offset_high = DECADE_PARTS[part]
        low, high = start + offset_low, start + offset_high
    high = min(high, MAX_YEAR)
    return (low, high) if is_year(low) and is_year(high) else None


def _years(low: int, high: int) -> Values | None:
    if not (is_year(low) and is_year(high)):
        return None
    return {"year_gte": min(low, high), "year_lte": max(low, high)}


def _range(m: re.Match[str], _: int) -> Values | None:
    return _years(int(m["a"]), int(m["b"]))


def _exact(m: re.Match[str], _: int) -> Values | None:
    return _years(int(m["y"]), int(m["y"]))


def _decade_exact(m: re.Match[str], _: int) -> Values | None:
    bounds = _decade_bounds(m, "y")
    return _years(*bounds) if bounds else None


def _decade_range(m: re.Match[str], _: int) -> Values | None:
    a = _decade_bounds(m, "a")
    b = _decade_bounds(m, "b")
    return _years(a[0], b[1]) if a and b else None


def _decade_gte(after: bool = False) -> Handler:
    def handler(m: re.Match[str], _: int) -> Values | None:
        bounds = _decade_bounds(m, "y")
        if not bounds:
            return None
        year = (bounds[1] + 1) if after else bounds[0]
        return {"year_gte": year} if is_year(year) else None

    return handler


def _decade_lte(before: bool = False) -> Handler:
    def handler(m: re.Match[str], _: int) -> Values | None:
        bounds = _decade_bounds(m, "y")
        if not bounds:
            return None
        if before and not m.groupdict().get("incl"):
            year = bounds[0] - 1
        else:
            year = bounds[1]
        return {"year_lte": year} if is_year(year) else None

    return handler


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


_DECADE_A = _decade_expr("a")
_DECADE_B = _decade_expr("b")
_DECADE_Y = _decade_expr("y")

YEAR_RULES: list[Rule] = [
    # "с 2010 по 2020", "от 2010 до 2020", "между 2010 и 2020"
    rule(
        rf"{WB}(?:с|от|между)\s+{year_group('a')}{YEAR_SUFFIX}\s+(?:по|до|и)\s+"
        rf"{year_group('b')}{YEAR_SUFFIX}(?:\s+включительно)?{WE}",
        _range,
    ),
    # "2010-2020", "в 2010–2020 годах"
    rule(rf"{WB}(?:в\s+)?{year_group('a')}{DASH}{year_group('b')}{YEAR_SUFFIX}", _range),
    # Decade ranges: "с 80-х по 90-е", "от 80-х до 2000-х", "между 80-ми и 90-ми", "80-е - 90-е", "80-х или 90-х"
    rule(
        rf"{WB}(?:с|от|между)\s+{_DECADE_A}\s+(?:по|до|и)\s+{_DECADE_B}(?:\s+включительно)?",
        _decade_range,
    ),
    rule(rf"{WB}(?:в\s+)?{_DECADE_A}(?:{DASH}|\s+(?:и|или)\s+){_DECADE_B}", _decade_range),
    # "годов 90-х и позже", "с 90-х и новее", "девяностые и свежее"
    rule(
        rf"{WB}(?:(?:с|от)\s+)?{_DECADE_Y}\s+и\s+(?:позже|позднее|новее|свежее){WE}",
        _decade_gte(after=False),
    ),
    # "90-х и раньше", "до 90-х и старше"
    rule(
        rf"{WB}(?:(?:до|по)\s+)?{_DECADE_Y}\s+и\s+(?:раньше|ранее|старше){WE}",
        _decade_lte(before=False),
    ),
    # "не позже 90-х", "по 90-е", "вплоть до 90-х"
    rule(
        rf"{WB}(?:не\s+позже|не\s+позднее|по|вплоть\s+до)\s+{_DECADE_Y}",
        _decade_lte(before=False),
    ),
    # "после 90-х", "новее нулевых"
    rule(
        rf"{WB}(?:после|позже|позднее|новее|свежее|моложе)\s+{_DECADE_Y}",
        _decade_gte(after=True),
    ),
    # "с 90-х", "от 80-х", "начиная с 90-х", "не раньше 90-х"
    rule(
        rf"{WB}(?:начиная\s+с|не\s+раньше|не\s+ранее|не\s+старше|с|от)\s+{_DECADE_Y}",
        _decade_gte(after=False),
    ),
    # "до 90-х", "раньше 90-х", "старше 90-х", "до 90-х включительно"
    rule(
        rf"{WB}(?:до|раньше|ранее|старше)\s+{_DECADE_Y}(?P<incl>\s+включительно)?",
        _decade_lte(before=True),
    ),
    # Standalone decades: "90-х", "в 80е", "годов 90-х", "восьмидесятые", "начало 2000-х"
    rule(rf"{WB}(?:(?:в|из|за)\s+)?{_DECADE_Y}", _decade_exact),
    # "за последний год", "за последнее время", "последние пару лет"
    rule(rf"{WB}(?:за\s+)?последн(?:ий|его)\s+(?:год|года?){WE}", _relative(1)),
    rule(rf"{WB}(?:за\s+)?последн(?:ее|его)\s+врем\w*{WE}", _recent),
    rule(
        rf"{WB}(?:за\s+)?последни[еих]\s+(?:несколько\s+(?:лет|годов)|(?P<n>\d{{1,2}}|{NUMBER_WORD})\s+(?:лет|года|год)){WE}",
        lambda m, cur: _last_years(m, cur) if m["n"] else _recent(m, cur),
    ),
    # Centuries: "21 век", "XXI века", "20 век"
    rule(rf"{WB}(?:в\s+)?(?:21|xxi)(?:-?[ймг])?\s+век\w*{WE}", const(year_gte=2001)),
    rule(rf"{WB}(?:в\s+)?(?:20|xx)(?:-?[ймг])?\s+век\w*{WE}", const(year_gte=1901, year_lte=2000)),
    # Relative years
    rule(rf"{WB}(?:(?:в\s+)?(?:этом|текущем)\s+году|этого\s+года){WE}", _relative(0)),
    rule(rf"{WB}(?:(?:в\s+)?прошлом\s+году|прошлого\s+года){WE}", _relative(1)),
    rule(rf"{WB}(?:(?:в\s+)?позапрошлом\s+году|позапрошлого\s+года){WE}", _relative(2)),
    # "2010 и позже", "с 2010 года и новее"
    rule(
        rf"{WB}(?:(?:с|от)\s+)?{year_group('y')}{YEAR_SUFFIX}\s+и\s+(?:позже|позднее|новее|свежее){WE}",
        _gte(),
    ),
    # "1999 и раньше", "до 1999 и старше"
    rule(
        rf"{WB}(?:(?:до|по)\s+)?{year_group('y')}{YEAR_SUFFIX}\s+и\s+(?:раньше|ранее|старше){WE}",
        _lte(),
    ),
    # "не позже 2010", "по 2010", "вплоть до 2010", "не моложе 2010"
    rule(
        rf"{WB}(?:не\s+позже|не\s+позднее|не\s+моложе|по|вплоть\s+до)\s+{year_group('y')}{YEAR_SUFFIX}",
        _lte(),
    ),
    # "после 2010", "позже 2010", "новее 2010", "моложе 2010"
    rule(
        rf"{WB}(?:после|позже|позднее|новее|свежее|моложе)\s+{year_group('y')}{YEAR_SUFFIX}",
        _gte(1),
    ),
    # "с 2010", "от 2010", "начиная с 2010", "не раньше 2010", "не старше 2010"
    rule(
        rf"{WB}(?:начиная\s+с|не\s+раньше|не\s+ранее|не\s+старше|с|от)\s+{year_group('y')}{YEAR_SUFFIX}",
        _gte(),
    ),
    # "до 2010", "раньше 2010", "старше 2010", "до 2010 включительно"
    rule(
        rf"{WB}(?:до|раньше|ранее|старше)\s+{year_group('y')}{YEAR_SUFFIX}(?P<incl>\s+включительно)?",
        _before,
    ),
    # Exact year: "2014", "в 2014 году", "2014 г."
    rule(rf"{WB}(?:(?:в|за|из)\s+)?{year_group('y')}{YEAR_SUFFIX}", _exact),
    # Negated qualitative age / recency (must precede positive qualitative rules; explicit years take priority)
    rule(
        rf"{AVOID_PREFIX}(?:стар(?:ые|ое|ый|ых|ым|ыми)|классик\w*|ретро){WE}",
        const(year_gte=OLD_BEFORE_YEAR),
    ),
    rule(
        rf"{AVOID_PREFIX}(?:свеж\w+|недавн\w+|современн\w+|новинк\w+){WE}",
        const(),
    ),
    # Qualitative recency / age
    rule(rf"{WB}(?:свеж\w+|недавн\w+|современн\w+|новинк\w+){WE}", _recent),
    rule(
        rf"{WB}(?:старые|старое|старый|старых|классик\w*|ретро){WE}",
        const(year_lte=OLD_BEFORE_YEAR - 1),
    ),
]
