"""
Tests for status and health endpoints.
"""
import pytest
from fastapi import status


def test_health_check(client):
    """Test basic health check."""
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"


def test_system_status(client):
    """Test system status endpoint."""
    response = client.get("/api/status")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert isinstance(data["services"], dict)


def test_metrics(client, test_db):
    """Test metrics endpoint."""
    response = client.get("/api/metrics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "games" in data
    assert "books" in data
    assert isinstance(data["games"]["total"], int)
    assert isinstance(data["books"]["total"], int)
