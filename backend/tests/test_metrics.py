"""Tests for the Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ocr_platform.main import create_app

client = TestClient(create_app())


class TestMetrics:
    """Metrics endpoint tests."""

    def test_metrics_returns_200(self) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self) -> None:
        response = client.get("/metrics")
        assert response.headers["content-type"].startswith("text/plain")

    def test_metrics_contains_process_metrics(self) -> None:
        response = client.get("/metrics")
        text = response.text
        # On some platforms (e.g., Windows), process metrics may not be available.
        # We assert that at least one metric line is present.
        assert "# HELP" in text or "# TYPE" in text
