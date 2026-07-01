"""Tests for the benchmark API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ocr_platform.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


class TestBenchmarkAPI:
    """Tests for the benchmark REST API."""

    def test_create_benchmark(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/benchmarks",
            json={
                "dataset_name": "english-test",
                "engines": ["mock"],
                "pages": [
                    {
                        "page_number": 1,
                        "ground_truth": "hello world",
                        "hypotheses": {
                            "mock": {"text": "hello world", "confidence": 0.99, "latency_ms": 10.0},
                        },
                    },
                ],
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert "benchmark_id" in data
        assert data["status"] == "completed"
        assert "GET /api/v1/benchmarks" in data["message"]

    def test_create_benchmark_no_engines(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/benchmarks",
            json={
                "dataset_name": "english-test",
                "engines": [],
                "pages": [{"page_number": 1, "ground_truth": "hello"}],
            },
        )
        assert response.status_code == 400
        assert "At least one engine" in response.json()["detail"]

    def test_create_benchmark_no_pages(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/benchmarks",
            json={
                "dataset_name": "english-test",
                "engines": ["mock"],
                "pages": [],
            },
        )
        assert response.status_code == 400
        assert "At least one page" in response.json()["detail"]

    def test_list_benchmarks(self, client: TestClient) -> None:
        # Create a benchmark first
        client.post(
            "/api/v1/benchmarks",
            json={
                "dataset_name": "english-test",
                "engines": ["mock"],
                "pages": [
                    {
                        "page_number": 1,
                        "ground_truth": "hello",
                        "hypotheses": {"mock": {"text": "hello"}},
                    },
                ],
            },
        )

        response = client.get("/api/v1/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert "benchmarks" in data
        assert data["total"] >= 1

    def test_get_benchmark(self, client: TestClient) -> None:
        create_response = client.post(
            "/api/v1/benchmarks",
            json={
                "dataset_name": "english-test",
                "engines": ["mock"],
                "pages": [
                    {
                        "page_number": 1,
                        "ground_truth": "hello",
                        "hypotheses": {"mock": {"text": "hello"}},
                    },
                ],
            },
        )
        benchmark_id = create_response.json()["benchmark_id"]

        response = client.get(f"/api/v1/benchmarks/{benchmark_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["benchmark_id"] == benchmark_id
        assert data["dataset_name"] == "english-test"
        assert data["status"] == "completed"

    def test_get_benchmark_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/benchmarks/nonexistent")
        assert response.status_code == 404

    def test_get_leaderboard(self, client: TestClient) -> None:
        create_response = client.post(
            "/api/v1/benchmarks",
            json={
                "dataset_name": "english-test",
                "engines": ["mock", "mistral"],
                "pages": [
                    {
                        "page_number": 1,
                        "ground_truth": "hello",
                        "hypotheses": {
                            "mock": {"text": "hallo", "confidence": 0.9, "latency_ms": 10.0},
                            "mistral": {"text": "hello", "confidence": 0.99, "latency_ms": 20.0},
                        },
                    },
                ],
            },
        )
        benchmark_id = create_response.json()["benchmark_id"]

        response = client.get(f"/api/v1/benchmarks/{benchmark_id}/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["benchmark_id"] == benchmark_id
        assert data["dataset_name"] == "english-test"
        assert data["total_pages"] == 1
        assert data["total_engines"] == 2
        assert len(data["leaderboard"]) == 2
        # Best engine should be first
        assert data["best_engine"] == data["leaderboard"][0]["engine"]

    def test_get_leaderboard_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/benchmarks/nonexistent/leaderboard")
        assert response.status_code == 404
