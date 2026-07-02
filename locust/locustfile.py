# Locust stress test file for the OCR Benchmark Platform
#
# Usage:
#   locust -f locust/locustfile.py --host http://localhost:8000
#
# Or via Docker:
#   docker run -p 8089:8089 -v $(pwd)/locust:/mnt/locust locustio/locust -f /mnt/locust/locustfile.py --host http://host.docker.internal:8000

from __future__ import annotations

import random

from locust import HttpUser, between, task


class ApiUser(HttpUser):
    """Simulates a user interacting with the OCR Platform API."""

    wait_time = between(1, 5)

    @task(10)
    def get_health(self) -> None:
        """Check API health — lightweight and frequent."""
        self.client.get("/health")

    @task(5)
    def list_jobs(self) -> None:
        """List all jobs."""
        # Note: there is no GET /jobs list endpoint in the current API;
        # we use GET /jobs/{job_id} with a known ID as a lightweight read.
        self.client.get("/api/v1/jobs/nonexistent-job-id")

    @task(5)
    def list_datasets(self) -> None:
        """List available datasets."""
        self.client.get("/api/v1/datasets")

    @task(5)
    def list_benchmarks(self) -> None:
        """List benchmark runs."""
        self.client.get("/api/v1/benchmarks")

    @task(3)
    def get_dataset(self) -> None:
        """Fetch a specific dataset with ground truth."""
        datasets = ["english", "urdu", "arabic", "hebrew", "mixed", "rotated", "low_quality", "tables"]
        dataset_id = random.choice(datasets)
        self.client.get(f"/api/v1/datasets/{dataset_id}")

    @task(2)
    def run_benchmark(self) -> None:
        """Submit a small benchmark run."""
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
        self.client.post("/api/v1/benchmarks", json=payload)

    @task(1)
    def get_metrics(self) -> None:
        """Scrape Prometheus metrics."""
        self.client.get("/metrics")


class HeavyUser(HttpUser):
    """Simulates a heavy user running multiple benchmarks concurrently."""

    wait_time = between(5, 15)

    @task(1)
    def run_heavy_benchmark(self) -> None:
        """Submit a larger benchmark with multiple pages and engines."""
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
        self.client.post("/api/v1/benchmarks", json=payload)
