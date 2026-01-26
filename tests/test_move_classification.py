"""
Tests for move classification service.
"""
import pytest
from app.services.move_classification_service import MoveClassificationService


def test_classify_best_move():
    """Test classification of best move."""
    service = MoveClassificationService()

    # Best move: same move
    result = service.classify_move("e2e4", "e2e4", "0.0", "0.0")
    assert result["label"] == "Best"


def test_classify_excellent_move():
    """Test classification of excellent move."""
    service = MoveClassificationService()

    # Excellent: small loss
    result = service.classify_move("e2e4", "e2e3", "-0.05", "0.0")
    assert result["label"] == "Excellent"


def test_classify_good_move():
    """Test classification of good move."""
    service = MoveClassificationService()

    # Good: moderate loss
    result = service.classify_move("e2e4", "e2e3", "-0.20", "0.0")
    assert result["label"] == "Good"


def test_classify_inaccuracy():
    """Test classification of inaccuracy."""
    service = MoveClassificationService()

    # Inaccuracy: larger loss
    result = service.classify_move("e2e4", "e2e3", "-0.60", "0.0")
    assert result["label"] == "Inaccuracy"


def test_classify_mistake():
    """Test classification of mistake."""
    service = MoveClassificationService()

    # Mistake: significant loss
    result = service.classify_move("e2e4", "e2e3", "-1.20", "0.0")
    assert result["label"] == "Mistake"


def test_classify_blunder():
    """Test classification of blunder."""
    service = MoveClassificationService()

    # Blunder: very large loss
    result = service.classify_move("e2e4", "e2e3", "-2.50", "0.0")
    assert result["label"] == "Blunder"


def test_classify_move_static():
    """Test static classify_move method with different scenarios."""
    # Test best move (same move)
    result = MoveClassificationService.classify_move("e2e4", "e2e4", "0.0", "0.0")
    assert result["label"] == "Best"
    assert result["centipawn_loss"] == 0

    # Test excellent move (small loss)
    result = MoveClassificationService.classify_move("e2e4", "e2e3", "-0.05", "0.0")
    assert result["label"] == "Excellent"

    # Test blunder (large loss)
    result = MoveClassificationService.classify_move("e2e4", "e2e3", "-2.5", "0.0")
    assert result["label"] == "Blunder"
