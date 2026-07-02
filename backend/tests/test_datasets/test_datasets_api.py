"""Tests for the dataset API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ocr_platform.main import create_app


class TestDatasetAPI:
    """Tests for the dataset REST API."""

    @pytest.fixture
    def client(self) -> TestClient:
        app = create_app()
        return TestClient(app)

    def test_list_datasets(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets")
        assert response.status_code == 200
        data = response.json()
        assert "datasets" in data
        assert data["total"] >= 8
        ids = {d["id"] for d in data["datasets"]}
        expected = {"english", "urdu", "arabic", "hebrew", "mixed", "rotated", "low_quality", "tables"}
        assert expected.issubset(ids)

    def test_get_english_dataset(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/english")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset"]["id"] == "english"
        assert data["dataset"]["category"] == "english"
        assert len(data["dataset"]["pages"]) > 0

    def test_get_urdu_dataset(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/urdu")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset"]["id"] == "urdu"
        assert data["dataset"]["language"] == "ur"

    def test_get_arabic_dataset(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/arabic")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset"]["id"] == "arabic"
        assert data["dataset"]["language"] == "ar"

    def test_get_hebrew_dataset(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/hebrew")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset"]["id"] == "hebrew"
        assert data["dataset"]["language"] == "he"

    def test_get_dataset_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/nonexistent")
        assert response.status_code == 404

    def test_get_dataset_page(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/english/pages/1")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_id"] == "english"
        assert data["page_number"] == 1
        assert data["ground_truth"] is not None
        assert len(data["ground_truth"]) > 0

    def test_get_dataset_page_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/english/pages/999")
        assert response.status_code == 404

    def test_get_dataset_page_dataset_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/nonexistent/pages/1")
        assert response.status_code == 404

    def test_list_categories(self, client: TestClient) -> None:
        response = client.get("/api/v1/datasets/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "english" in data
        assert "arabic" in data
        assert "hebrew" in data
        assert "urdu" in data
