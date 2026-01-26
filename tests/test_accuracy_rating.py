"""
Tests for accuracy and rating service.
"""
import pytest
from app.services.accuracy_rating_service import AccuracyRatingService


def test_calculate_move_accuracy():
    """Test move accuracy calculation."""
    service = AccuracyRatingService()

    # Best move
    accuracy = service.calculate_move_accuracy(0)
    assert accuracy == 100

    # Small loss
    accuracy = service.calculate_move_accuracy(10)
    assert 90 <= accuracy <= 100

    # Large loss
    accuracy = service.calculate_move_accuracy(100)
    assert accuracy < 50


def test_calculate_game_accuracy():
    """Test game accuracy calculation."""
    service = AccuracyRatingService()

    # Mock classifications with centipawn_loss
    classifications = [
        {"centipawn_loss": 0, "label": "Best"},
        {"centipawn_loss": 5, "label": "Excellent"},
        {"centipawn_loss": 20, "label": "Good"},
        {"centipawn_loss": 40, "label": "Inaccuracy"},
        {"centipawn_loss": 75, "label": "Mistake"},
        {"centipawn_loss": 150, "label": "Blunder"},
    ]

    result = service.calculate_game_accuracy(classifications)
    assert 0 <= result["accuracy"] <= 100
    assert "move_accuracies" in result
    assert "blunder_count" in result


def test_estimate_rating():
    """Test rating estimation."""
    service = AccuracyRatingService()

    # High accuracy should give higher rating
    high_result = service.estimate_rating(90, 0)
    low_result = service.estimate_rating(50, 5)

    assert high_result["estimated_rating"] > low_result["estimated_rating"]
    assert 0 <= high_result["estimated_rating"] <= 3000
    assert 0 <= low_result["estimated_rating"] <= 3000


def test_estimate_rating_confidence():
    """Test rating confidence levels."""
    service = AccuracyRatingService()

    # High accuracy = high confidence
    result = service.estimate_rating(95, 0)
    assert result["confidence"] in ["low", "medium", "high"]
    assert result["estimated_rating"] > 0

    # Low accuracy = lower confidence
    result = service.estimate_rating(40, 3)
    assert result["confidence"] in ["low", "medium", "high"]
