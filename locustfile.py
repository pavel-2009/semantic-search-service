"""Locust load test for the search endpoint."""

import random

from locust import HttpUser, between, task


SEARCH_QUERIES = (
    "фильм про космос",
    "психологический триллер про потерю памяти",
    "комедия для семейного просмотра",
    "фильм про путешествие во времени",
)


class SearchUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def search_movies(self) -> None:
        self.client.post(
            "/api/v1/search",
            json={"query": random.choice(SEARCH_QUERIES), "top_k": 10},
            name="/api/v1/search",
        )
