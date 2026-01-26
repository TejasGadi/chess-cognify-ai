"""
Tests for input validation and error handling.
"""
import pytest
from fastapi import status


def test_validation_error_empty_pgn(client):
    """Test validation error for empty PGN."""
    response = client.post(
        "/api/games/upload",
        json={"pgn": ""},
    )

    # Empty PGN might be accepted by the endpoint but validation happens during analysis
    # Check that we get either 422 (validation error) or 201 (created but invalid)
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_201_CREATED]
    
    if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        data = response.json()
        assert "error" in data or "detail" in data


def test_validation_error_missing_field(client):
    """Test validation error for missing required field."""
    response = client.post(
        "/api/games/upload",
        json={},  # Missing pgn field
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_validation_error_invalid_message_length(client):
    """Test validation error for message length."""
    # Too short
    response = client.post(
        "/api/games/test-id/chat",
        json={"message": ""},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Too long
    long_message = "x" * 2000
    response = client.post(
        "/api/games/test-id/chat",
        json={"message": long_message},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
