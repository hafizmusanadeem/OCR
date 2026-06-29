"""Tests for the logging middleware."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ocr_platform.main import create_app

client = TestClient(create_app())


class TestLoggingMiddleware:
    """Logging middleware tests."""

    def test_request_logs_on_success(self, capsys) -> None:
        client.get("/health")
        captured = capsys.readouterr()
        # Structlog JSON output should contain the request event
        assert "request" in captured.out or captured.err

    def test_request_logs_include_method_and_path(self, capsys) -> None:
        client.get("/health")
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "GET" in output
        assert "/health" in output

    def test_request_logs_status_code(self, capsys) -> None:
        client.get("/health")
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "200" in output
