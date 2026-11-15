"""Keywords, filters and limits extraction"""

from yargy import Parser, rule, or_, and_
from yargy.predicates import gram, type, dictionary
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact
from yargy.relations import gnc_relation


YearFact = fact(
    "Year Factor",
    ['year', 'min_year', 'max_year']
)

def is_year(value):
    return value.isdigit() and 1900 <= int(value) <= 2030

class FilterExtractor:
    def __init__(self):

