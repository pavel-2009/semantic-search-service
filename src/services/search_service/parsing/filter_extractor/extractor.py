"""Extract year and rating filters from a free-form Russian query.

Examples:
    "фильмы 90-х с рейтингом выше 7.5"  -> 1990..1999, rating >= 7.5
    "комедии после 2010 года"            -> year >= 2011
    "триллер с 2005 по 2015"             -> 2005..2015
    "что-нибудь свежее, оценка 8+"       -> year >= current-4, rating >= 8
"""

import re
from datetime import date

from src.services.search_service.parsing.filter_extractor.rating_rules import RATING_RULES
from src.services.search_service.parsing.filter_extractor.rules import Rule
from src.services.search_service.parsing.filter_extractor.schemas import ExtractedFilters
from src.services.search_service.parsing.filter_extractor.year_rules import YEAR_RULES

RULES: list[Rule] = [*RATING_RULES, *YEAR_RULES]


class FilterExtractor:
    """Find year and rating constraints in a query and cut them out of its text.

    Rules are applied in order; the first rule that sets a field wins.
    """

    def __init__(self, current_year: int | None = None) -> None:
        self.current_year = current_year or date.today().year

    def extract(self, text: str) -> ExtractedFilters:
        """Return filters found in text and the text with those phrases removed."""
        filters: dict[str, int | float] = {}

        def apply(rule: Rule, match: re.Match[str]) -> str:
            values = rule.handler(match, self.current_year)
            if values is None:
                return match.group(0)
            for field, value in values.items():
                filters.setdefault(field, value)
            return " "

        working = text.lower().replace("ё", "е")
        for rule in RULES:
            working = rule.pattern.sub(lambda m, rule=rule: apply(rule, m), working)

        return ExtractedFilters(text=self._clean(working), **filters)

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"(?:^|\s)[,.;:\-–—]+(?=\s|$)", " ", text)
        return " ".join(text.split()).strip(" ,.;:-")
