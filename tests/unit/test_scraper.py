"""Tests for scraper module, API responses processing and data validation."""

import pytest

from src.scraper.schemas import (
    PoiskKinoCountry,
    PoiskKinoGenre,
    PoiskKinoPerson,
    PoiskKinoMovie,
    Movie,
    MoviesDocument
)


class MockKinopoiskAPI:
    """Mock class for KinopoiskAPI to simulate API responses."""

    def get_valid_movie_data(self) -> dict:
        return {
            "docs": [
                {
                    "id": 1,
                    "name": "Интерстеллар",
                    "year": 2014,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "драма"}],
                    "rating": {"kp": 8.6},
                    "description": "Путешествие через космос и время.",
                },
                {
                    "id": 2,
                    "name": "Начало",
                    "year": 2010,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.7},
                    "description": "Вор проникает в сны людей.",
                },
                {
                    "id": 3,
                    "name": "Матрица",
                    "year": 1999,
                    "countries": [{"name": "США"}, {"name": "Австралия"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.5},
                    "description": "Программист узнает правду о реальности.",
                },
            ],
            "page": 1,
            "pages": 1,
        }

    def get_invalid_movie_data(self) -> dict:
        return {
            "docs": [
                {
                    "id": 1,
                    "name": "Интерстеллар",
                    "year": 2014,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "драма"}],
                    "rating": {"kp": 8.6},
                    "description": "Путешествие через космос и время.",
                },
                {
                    "id": "invalid",
                    "name": "Начало",
                    "year": 2010,
                    "countries": [{"name": "США"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.7},
                    "description": "Вор проникает в сны людей.",
                },
                {
                    "id": 3,
                    "name": "Матрица",
                    "year": 1999,
                    "countries": [{"name": "США"}, {"name": "Австралия"}],
                    "genres": [{"name": "фантастика"}, {"name": "боевик"}],
                    "rating": {"kp": 8.5},
                    "description": "Программист узнает правду о реальности.",
                },
            ],
            "page": 1,
            "pages": 1,
        }
