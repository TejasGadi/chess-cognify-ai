"""
Tests for database models.
"""
import pytest
from app.models.game import Game, EngineAnalysis, MoveReview, GameSummary
from app.models.book import Book
from app.models.chat import ChatMessage
import uuid


def test_create_game(test_db):
    """Test creating a game."""
    game = Game(
        game_id=str(uuid.uuid4()),
        pgn="1. e4 e5 2. Nf3 Nc6 1-0",
        metadata={"test": True},
    )

    test_db.add(game)
    test_db.commit()

    assert game.game_id is not None
    assert game.pgn == "1. e4 e5 2. Nf3 Nc6 1-0"


def test_create_engine_analysis(test_db):
    """Test creating engine analysis."""
    game_id = str(uuid.uuid4())
    analysis = EngineAnalysis(
        game_id=game_id,
        ply=1,
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        played_move="e5",
        best_move="e5",
        eval_before="0.0",
        eval_after="0.0",
        eval_best="0.0",
    )

    test_db.add(analysis)
    test_db.commit()

    assert analysis.id is not None
    assert analysis.game_id == game_id


def test_create_move_review(test_db):
    """Test creating move review."""
    game_id = str(uuid.uuid4())
    review = MoveReview(
        game_id=game_id,
        ply=1,
        label="Best",
        centipawn_loss=0,
        explanation="A solid opening move",
        accuracy=100,
    )

    test_db.add(review)
    test_db.commit()

    assert review.id is not None
    assert review.label == "Best"


def test_create_game_summary(test_db):
    """Test creating game summary."""
    game_id = str(uuid.uuid4())
    summary = GameSummary(
        game_id=game_id,
        accuracy=85,
        estimated_rating=1500,
        rating_confidence="medium",
        weaknesses=["Tactical awareness"],
    )

    test_db.add(summary)
    test_db.commit()

    assert summary.id is not None
    assert summary.accuracy == 85


def test_create_book(test_db):
    """Test creating book."""
    book = Book(
        book_id=str(uuid.uuid4()),
        title="Test Chess Book",
        author="Test Author",
        filename="test.pdf",
        total_pages=100,
        total_chunks=500,
    )

    test_db.add(book)
    test_db.commit()

    assert book.book_id is not None
    assert book.title == "Test Chess Book"


def test_create_chat_message(test_db):
    """Test creating chat message."""
    game_id = str(uuid.uuid4())
    message = ChatMessage(
        game_id=game_id,
        session_id="test-session",
        role="user",
        content="What was the best move?",
        context_type="game",
        context_id=game_id,
    )

    test_db.add(message)
    test_db.commit()

    assert message.id is not None
    assert message.role == "user"
