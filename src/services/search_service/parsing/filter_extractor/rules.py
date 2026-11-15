"""Shared building blocks for extraction rules."""

import re
from collections.abc import Callable
from typing import NamedTuple

MIN_YEAR = 1900
MAX_YEAR = 2030
MAX_RATING = 10.0

Values = dict[str, int | float]
Handler = Callable[[re.Match[str], int], Values | None]


class Rule(NamedTuple):
    """A regex plus a handler returning the filters it produces (None = skip)."""

    pattern: re.Pattern[str]
    handler: Handler


def rule(pattern: str, handler: Handler) -> Rule:
    return Rule(re.compile(pattern, re.IGNORECASE), handler)


def const(**values: int | float) -> Handler:
    return lambda _m, _current: dict(values)


def is_year(value: int) -> bool:
    return MIN_YEAR <= value <= MAX_YEAR


def year_group(name: str) -> str:
    return rf"(?<!\d)(?P<{name}>(?:19|20)\d{{2}})(?!\d)"


def number_group(name: str) -> str:
    return rf"(?<![\d.,])(?P<{name}>\d{{1,2}}(?:[.,]\d{{1,2}})?)(?!\d)"


DASH = r"\s*[-–—]\s*"
