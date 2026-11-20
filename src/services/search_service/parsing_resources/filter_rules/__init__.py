"""Predefined year and rating extraction rules."""

from src.services.search_service.parsing_resources.filter_rules.rating_rules import RATING_RULES
from src.services.search_service.parsing_resources.filter_rules.rules import Rule
from src.services.search_service.parsing_resources.filter_rules.year_rules import YEAR_RULES

RULES: list[Rule] = [*RATING_RULES, *YEAR_RULES]
