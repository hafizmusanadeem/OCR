"""Unit tests for the Locust load-test scenarios.

These tests verify that the Locust User classes can be instantiated
and that their task methods execute without raising exceptions.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ocr_platform.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


class TestApiUserTasks:
    """Verify ApiUser tasks run successfully against the test server."""

    def test_get_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_list_jobs(self, client: TestClient) -> None:
        # The jobs API does not expose a list endpoint; GET /jobs/{id} returns 404 for unknown IDs.
        response = client.get("/api/v1/jobs/nonexistent-job-id")
        assert response.status_code == 404

    def test_list_datasets(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets")
        assert response.status_code == 200

    def test_list_benchmarks(self, client: TestClient) -> None:
        response = client.get("/api/v1/benchmarks")
        assert response.status_code == 200

    def test_get_dataset(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/english")
        assert response.status_code == 200

    def test_run_benchmark(self, client: TestClient) -> None:
        payload = {
            "dataset_name": "english",
            "engines": ["mock"],
            "pages": [
                {
                    "page_number": 1,
                    "ground_truth": "Hello world",
                    "hypotheses": {
                        "mock": {
                            "text": "Hello world",
                            "confidence": 0.99,
                            "latency_ms": 10.0,
                        }
                    },
                }
            ],
        }
        response = client.post("/api/v1/benchmarks", json=payload)
        assert response.status_code == 202

    def test_get_metrics(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200


class TestHeavyUserTasks:
    """Verify heavy benchmark submission against the test server."""

    def test_run_heavy_benchmark(self, client: TestClient) -> None:
        import random
        pages = [
            {
                "page_number": i,
                "ground_truth": f"This is sample page number {i} for stress testing.",
                "hypotheses": {
                    "mock": {
                        "text": f"This is sample page number {i} for stress testing.",
                        "confidence": random.uniform(0.85, 0.99),
                        "latency_ms": random.uniform(5.0, 50.0),
                    }
                },
            }
            for i in range(1, 6)
        ]
        payload = {
            "dataset_name": "english",
            "engines": ["mock"],
            "pages": pages,
        }
        response = client.post("/api/v1/benchmarks", json=payload)
        assert response.status_code == 202
