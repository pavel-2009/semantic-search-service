"""Performance and load tests for the semantic search service."""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median, stdev
from typing import List, Dict, Any

import pytest
import requests
from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import SearchRequest


class TestPerformance:
    """Performance tests for search endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "warmup", "top_k": 1},
        )
        assert response.status_code == 200
        return client

    def test_search_latency(self, client):
        """Test search endpoint latency with multiple queries."""
        queries = [
            "interstellar",
            "inception",
            "the dark knight",
            "drama",
            "action",
            "sci-fi",
            "комедия",
            "триллер",
            "романтика",
            "фантастика"
        ]
        
        latencies = []
        results_count = []
        
        print("\n📊 Search Latency Test")
        print("-" * 60)
        
        for query in queries:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search",
                json={"query": query, "top_k": 5}
            )
            latency = (time.perf_counter() - start) * 1000  # ms
            latencies.append(latency)
            
            assert response.status_code == 200
            data = response.json()
            results_count.append(data.get("total", 0))
            
            print(f"  {query[:20]:20} | {latency:6.2f}ms | {data.get('total', 0):3} results")
        
        # Статистика
        print("-" * 60)
        print(f"  Average: {mean(latencies):6.2f}ms")
        print(f"  Median:  {median(latencies):6.2f}ms")
        print(f"  Max:     {max(latencies):6.2f}ms")
        print(f"  Min:     {min(latencies):6.2f}ms")
        if len(latencies) > 1:
            print(f"  StdDev:  {stdev(latencies):6.2f}ms")
        
        # Проверяем, что средняя задержка < 500ms
        assert mean(latencies) < 500, f"Average latency {mean(latencies):.2f}ms > 500ms"
        assert max(latencies) < 1000, f"Max latency {max(latencies):.2f}ms > 1000ms"

    def test_concurrent_search(self, client):
        """Test concurrent search requests."""
        queries = [
            "interstellar", "inception", "dark knight", 
            "drama", "action", "sci-fi", "comedy", 
            "thriller", "romance", "fantasy"
        ]
        
        def do_search(query: str) -> tuple[float, int, int]:
            """Execute a single search request."""
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search",
                json={"query": query, "top_k": 5}
            )
            latency = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return latency, response.status_code, data.get("total", 0)
            return latency, response.status_code, 0
        
        # Запускаем 50 запросов параллельно (10 потоков * 5 запросов каждый)
        total_requests = 50
        concurrency_level = 10
        
        print(f"\n📊 Concurrent Search Test")
        print(f"  Total requests: {total_requests}")
        print(f"  Concurrency: {concurrency_level}")
        print("-" * 60)
        
        with ThreadPoolExecutor(max_workers=concurrency_level) as executor:
            futures = []
            for i in range(total_requests):
                query = queries[i % len(queries)]
                futures.append(executor.submit(do_search, query))
            
            results = [f.result() for f in as_completed(futures)]
        
        # Анализ результатов
        latencies = [r[0] for r in results]
        statuses = [r[1] for r in results]
        results_counts = [r[2] for r in results]
        
        success_count = sum(1 for s in statuses if s == 200)
        success_rate = (success_count / len(statuses)) * 100
        
        print(f"\n  Results:")
        print(f"    Success rate: {success_rate:.1f}% ({success_count}/{len(statuses)})")
        print(f"    Avg latency:  {mean(latencies):6.2f}ms")
        print(f"    Median:       {median(latencies):6.2f}ms")
        print(f"    Max:          {max(latencies):6.2f}ms")
        print(f"    Min:          {min(latencies):6.2f}ms")
        print(f"    Avg results:  {mean(results_counts):.1f}")
        
        # Проверяем, что минимум 95% запросов успешны
        assert success_rate > 95, f"Success rate {success_rate:.1f}% < 95%"
        # Проверяем, что средняя задержка < 1с
        assert mean(latencies) < 1000, f"Average latency {mean(latencies):.2f}ms > 1000ms"

    @pytest.mark.slow
    def test_load_test_with_different_queries(self, client):
        """Full load test with different query types."""
        test_cases = [
            {"query": "interstellar", "description": "Short English"},
            {"query": "фильм про космос", "description": "Short Russian"},
            {"query": "криминальная драма про мафию", "description": "Medium Russian"},
            {"query": "batman", "description": "Short English"},
            {"query": "comedy", "description": "Short English"},
            {"query": "thriller", "description": "Short English"},
            {"query": "романтическая комедия", "description": "Medium Russian"},
            {"query": "a" * 100, "description": "Long query"},
            {"query": "action movie", "description": "Short English"},
            {"query": "sci-fi", "description": "Short English"},
        ]
        
        results = []
        
        print("\n📊 Load Test Results")
        print("-" * 60)
        
        for test_case in test_cases:
            query = test_case["query"]
            desc = test_case["description"]
            
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search",
                json={"query": query, "top_k": 10}
            )
            latency = (time.perf_counter() - start) * 1000
            
            status = "✅" if response.status_code == 200 else "❌"
            data = response.json() if response.status_code == 200 else {}
            
            results.append({
                "query": query,
                "description": desc,
                "latency": latency,
                "status": response.status_code,
                "results": data.get("total", 0)
            })
            
            print(f"  {status} {desc:20} | {latency:6.2f}ms | {data.get('total', 0):3} results")
        
        # Статистика
        latencies = [r["latency"] for r in results]
        statuses = [r["status"] for r in results]
        
        print("-" * 60)
        print(f"  Success rate: {sum(1 for s in statuses if s == 200) / len(statuses) * 100:.1f}%")
        print(f"  Avg latency:  {mean(latencies):6.2f}ms")
        print(f"  Max latency:  {max(latencies):6.2f}ms")
        
        # Проверяем, что все запросы успешны
        assert all(r["status"] == 200 for r in results)

    def test_search_with_filters_performance(self, client):
        """Performance test for search with filters."""
        test_cases = [
            {
                "query": "drama",
                "filters": {
                    "year": {"gte": 2010},
                    "rating": {"gte": 7.0}
                }
            },
            {
                "query": "action",
                "filters": {
                    "year": {"gte": 2000, "lte": 2020},
                    "genre": ["action"]
                }
            },
            {
                "query": "sci-fi",
                "filters": {
                    "rating": {"gte": 8.0},
                    "genre": ["sci-fi", "adventure"]
                }
            },
            {
                "query": "comedy",
                "filters": {
                    "year": {"gte": 2015},
                    "country": "USA"
                }
            }
        ]
        
        latencies = []
        
        print("\n📊 Search with Filters Performance")
        print("-" * 60)
        
        for test_case in test_cases:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search",
                json={
                    "query": test_case["query"],
                    "top_k": 5,
                    "filters": test_case["filters"]
                }
            )
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            
            assert response.status_code == 200
            data = response.json()
            
            print(f"  {test_case['query']:10} | {latency:6.2f}ms | {data.get('total', 0):3} results")
        
        print("-" * 60)
        print(f"  Average: {mean(latencies):6.2f}ms")
        print(f"  Max:     {max(latencies):6.2f}ms")
        
        # Проверяем, что средняя задержка < 1с
        assert mean(latencies) < 1000

    def test_top_k_impact(self, client):
        """Test impact of different top_k values on performance."""
        top_k_values = [1, 5, 10, 25, 50, 100]
        results = []
        
        print("\n📊 Top-K Impact on Performance")
        print("-" * 60)
        
        for top_k in top_k_values:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search",
                json={"query": "interstellar", "top_k": top_k}
            )
            latency = (time.perf_counter() - start) * 1000
            
            assert response.status_code == 200
            data = response.json()
            
            results.append({
                "top_k": top_k,
                "latency": latency,
                "results": data.get("total", 0)
            })
            
            print(f"  top_k={top_k:3} | {latency:6.2f}ms | {data.get('total', 0):3} results")
        
        print("-" * 60)
        avg_latency = mean(r["latency"] for r in results)
        print(f"  Average: {avg_latency:6.2f}ms")
        
        # Проверяем, что даже с top_k=100 задержка < 2с
        max_latency = max(r["latency"] for r in results)
        assert max_latency < 2000, f"Max latency with top_k=100 is {max_latency:.2f}ms"

    @pytest.mark.slow
    def test_sustained_load(self, client):
        """Test sustained load over time (60 seconds)."""
        queries = [
            "interstellar", "inception", "dark knight",
            "drama", "action", "sci-fi",
            "комедия", "триллер", "фантастика"
        ]
        
        durations = []
        request_count = 0
        error_count = 0
        start_time = time.perf_counter()
        
        print("\n📊 Sustained Load Test (60 seconds)")
        print("-" * 60)
        print("Running...", end="", flush=True)
        
        # Запускаем запросы в течение 60 секунд
        while time.perf_counter() - start_time < 60:
            query = queries[request_count % len(queries)]
            
            req_start = time.perf_counter()
            response = client.post(
                "/api/v1/search",
                json={"query": query, "top_k": 5}
            )
            req_duration = (time.perf_counter() - req_start) * 1000
            
            durations.append(req_duration)
            request_count += 1
            
            if response.status_code != 200:
                error_count += 1
            
            # Маленькая задержка между запросами
            time.sleep(0.1)
        
        print(" Done!")
        print("-" * 60)
        
        # Статистика
        print(f"  Total requests: {request_count}")
        print(f"  Errors: {error_count} ({error_count/request_count*100:.1f}%)")
        print(f"  Avg latency:  {mean(durations):6.2f}ms")
        print(f"  Median:       {median(durations):6.2f}ms")
        print(f"  Max:          {max(durations):6.2f}ms")
        print(f"  Min:          {min(durations):6.2f}ms")
        print(f"  Requests/sec: {request_count / 60:.1f}")
        
        # Проверки
        error_rate = error_count / request_count * 100
        assert error_rate < 5, f"Error rate {error_rate:.1f}% > 5%"
        assert mean(durations) < 1000, f"Average latency {mean(durations):.2f}ms > 1000ms"

    def test_memory_usage(self, client):
        """Test memory usage during searches (basic check)."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"\n📊 Memory Usage Test")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        
        # Выполняем много запросов
        for i in range(100):
            response = client.post(
                "/api/v1/search",
                json={"query": f"test query {i}", "top_k": 5}
            )
            assert response.status_code == 200
            
            if i % 20 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"  After {i:3} requests: {current_memory:.1f} MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        
        # Проверяем, что память не растёт бесконтрольно (менее 200MB)
        assert memory_increase < 200, f"Memory increased by {memory_increase:.1f} MB > 200MB"