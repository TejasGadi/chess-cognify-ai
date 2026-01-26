"""
Integration tests for game API endpoints.
"""
import pytest
from fastapi import status


def test_upload_game(client, sample_pgn):
    """Test uploading a game."""
    response = client.post(
        "/api/games/upload",
        json={"pgn": sample_pgn, "metadata": {"test": True}},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "game_id" in data
    assert data["pgn"] == sample_pgn


def test_upload_invalid_game(client, invalid_pgn):
    """Test uploading invalid PGN."""
    response = client.post(
        "/api/games/upload",
        json={"pgn": invalid_pgn},
    )

    # Should still create game record, validation happens during analysis
    assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]


def test_get_game(client, sample_pgn):
    """Test getting game details."""
    # First upload
    upload_response = client.post(
        "/api/games/upload",
        json={"pgn": sample_pgn},
    )
    game_id = upload_response.json()["game_id"]

    # Then get
    response = client.get(f"/api/games/{game_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["game_id"] == game_id


def test_get_nonexistent_game(client):
    """Test getting non-existent game."""
    response = client.get("/api/games/nonexistent-id")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_game_moves(client, test_db, sample_pgn):
    """Test getting game moves."""
    # Upload game
    upload_response = client.post(
        "/api/games/upload",
        json={"pgn": sample_pgn},
    )
    game_id = upload_response.json()["game_id"]

    # Get moves (may be empty if not analyzed yet)
    response = client.get(f"/api/games/{game_id}/moves")

    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_get_game_summary(client, test_db, sample_pgn):
    """Test getting game summary."""
    # Upload game
    upload_response = client.post(
        "/api/games/upload",
        json={"pgn": sample_pgn},
    )
    game_id = upload_response.json()["game_id"]

    # Get summary (may 404 if not analyzed)
    response = client.get(f"/api/games/{game_id}/summary")

    # Should either return summary or 404 if not analyzed
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


def test_get_game_review(client, test_db, sample_pgn):
    """Test getting complete game review."""
    # Upload game
    upload_response = client.post(
        "/api/games/upload",
        json={"pgn": sample_pgn},
    )
    game_id = upload_response.json()["game_id"]

    # Get review
    response = client.get(f"/api/games/{game_id}/review")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "game_id" in data
    assert "game" in data
    assert "moves" in data
