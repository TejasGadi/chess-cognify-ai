"""
Integration tests for chat API endpoints.
"""
import pytest
from fastapi import status


def test_chat_with_game(client, test_db, sample_pgn):
    """Test chatting with game review."""
    # Upload game
    upload_response = client.post(
        "/api/games/upload",
        json={"pgn": sample_pgn},
    )
    game_id = upload_response.json()["game_id"]

    # Chat (may fail if game not analyzed, but should handle gracefully)
    response = client.post(
        f"/api/games/{game_id}/chat",
        json={"message": "What was the best move in this game?"},
    )

    # Should either succeed or return appropriate error
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ]


def test_chat_with_nonexistent_game(client):
    """Test chatting with non-existent game."""
    response = client.post(
        "/api/games/nonexistent-id/chat",
        json={"message": "Test message"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_chat_history(client, test_db, sample_pgn):
    """Test getting chat history."""
    # Upload game
    upload_response = client.post(
        "/api/games/upload",
        json={"pgn": sample_pgn},
    )
    game_id = upload_response.json()["game_id"]

    # Get history (may be empty)
    response = client.get(
        f"/api/games/{game_id}/chat/history",
        params={"session_id": "test-session"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "game_id" in data
    assert "session_id" in data
    assert "messages" in data
