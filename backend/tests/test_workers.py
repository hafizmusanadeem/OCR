"""Tests for the worker health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ocr_platform.main import create_app

client = TestClient(create_app())


class TestWorkersHealth:
    """Tests for the worker health check endpoint."""

    def test_workers_health_returns_200(self) -> None:
        response = client.get("/api/v1/workers/health")
        assert response.status_code == 200

    def test_workers_health_response_structure(self) -> None:
        response = client.get("/api/v1/workers/health")
        data = response.json()
        assert "status" in data
        assert "active_workers" in data
        assert "registered_workers" in data
        assert "workers" in data
        assert isinstance(data["active_workers"], int)
        assert isinstance(data["registered_workers"], int)
        assert isinstance(data["workers"], list)
