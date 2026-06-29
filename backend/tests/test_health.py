"""Tests for the health check endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ocr_platform.main import create_app

client = TestClient(create_app())


class TestHealth:
    """Health endpoint tests."""

    def test_health_returns_200(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["environment"] == "development"
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], float)

    def test_health_uptime_increases(self) -> None:
        response1 = client.get("/health")
        uptime1 = response1.json()["uptime_seconds"]

        response2 = client.get("/health")
        uptime2 = response2.json()["uptime_seconds"]

        assert uptime2 >= uptime1
