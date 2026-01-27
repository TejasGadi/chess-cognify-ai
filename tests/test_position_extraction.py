"""
Tests for position extraction and validation (multi-step reasoning).
"""
import pytest
import chess
from app.agents.position_extraction_agent import PositionExtractionAgent
from app.utils.position_validator import PositionValidator
from app.schemas.llm_output import PositionExtractionOutput


@pytest.fixture
def position_extraction_agent():
    """Create PositionExtractionAgent instance."""
    return PositionExtractionAgent()


@pytest.fixture
def position_validator():
    """Create PositionValidator instance."""
    return PositionValidator()


@pytest.fixture
def starting_position_fen():
    """Starting position FEN."""
    return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


@pytest.fixture
def test_position_fen():
    """Test position FEN (after e4 e5)."""
    return "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"


class TestPositionValidator:
    """Test position validator functionality."""

    def test_get_actual_pieces_from_fen_starting_position(self, position_validator, starting_position_fen):
        """Test extracting pieces from starting position."""
        actual_pieces = position_validator._get_actual_pieces_from_fen(starting_position_fen)
        
        assert "white" in actual_pieces
        assert "black" in actual_pieces
        
        # Check white pieces
        assert len(actual_pieces["white"]["King"]) == 1
        assert actual_pieces["white"]["King"][0] == "e1"
        assert len(actual_pieces["white"]["Pawns"]) == 8
        
        # Check black pieces
        assert len(actual_pieces["black"]["King"]) == 1
        assert actual_pieces["black"]["King"][0] == "e8"
        assert len(actual_pieces["black"]["Pawns"]) == 8

    def test_validate_extraction_perfect_match(self, position_validator, starting_position_fen):
        """Test validation with perfect match."""
        # Create extraction that matches actual position
        extraction = PositionExtractionOutput(
            white_pieces={
                "King": ["e1"],
                "Queen": ["d1"],
                "Rooks": ["a1", "h1"],
                "Bishops": ["c1", "f1"],
                "Knights": ["b1", "g1"],
                "Pawns": ["a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2"]
            },
            black_pieces={
                "King": ["e8"],
                "Queen": ["d8"],
                "Rooks": ["a8", "h8"],
                "Bishops": ["c8", "f8"],
                "Knights": ["b8", "g8"],
                "Pawns": ["a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7"]
            },
            active_color="White",
            last_move_square=None,
            verification_status="verified",
            confidence=1.0
        )
        
        result = position_validator.validate_extraction(extraction, starting_position_fen)
        
        assert result.is_valid is True
        assert len(result.discrepancies) == 0
        assert result.confidence_score >= 0.9

    def test_validate_extraction_with_discrepancies(self, position_validator, starting_position_fen):
        """Test validation with discrepancies (hallucinated piece)."""
        # Create extraction with hallucinated knight on b5
        extraction = PositionExtractionOutput(
            white_pieces={
                "King": ["e1"],
                "Queen": ["d1"],
                "Rooks": ["a1", "h1"],
                "Bishops": ["c1", "f1"],
                "Knights": ["b1", "b5"],  # b5 is hallucinated
                "Pawns": ["a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2"]
            },
            black_pieces={
                "King": ["e8"],
                "Queen": ["d8"],
                "Rooks": ["a8", "h8"],
                "Bishops": ["c8", "f8"],
                "Knights": ["b8", "g8"],
                "Pawns": ["a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7"]
            },
            active_color="White",
            last_move_square=None,
            verification_status="needs_review",
            confidence=0.8
        )
        
        result = position_validator.validate_extraction(extraction, starting_position_fen)
        
        assert result.is_valid is False
        assert len(result.discrepancies) > 0
        assert any("b5" in disc or "hallucinated" in disc.lower() for disc in result.discrepancies)
        assert result.confidence_score < 0.9

    def test_validate_extraction_missing_piece(self, position_validator, starting_position_fen):
        """Test validation with missing piece."""
        # Create extraction missing a pawn
        extraction = PositionExtractionOutput(
            white_pieces={
                "King": ["e1"],
                "Queen": ["d1"],
                "Rooks": ["a1", "h1"],
                "Bishops": ["c1", "f1"],
                "Knights": ["b1", "g1"],
                "Pawns": ["a2", "b2", "c2", "d2", "e2", "f2", "g2"]  # Missing h2
            },
            black_pieces={
                "King": ["e8"],
                "Queen": ["d8"],
                "Rooks": ["a8", "h8"],
                "Bishops": ["c8", "f8"],
                "Knights": ["b8", "g8"],
                "Pawns": ["a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7"]
            },
            active_color="White",
            last_move_square=None,
            verification_status="needs_review",
            confidence=0.8
        )
        
        result = position_validator.validate_extraction(extraction, starting_position_fen)
        
        assert result.is_valid is False
        assert len(result.discrepancies) > 0
        assert any("h2" in disc or "missed" in disc.lower() for disc in result.discrepancies)

    def test_normalize_piece_list(self, position_validator):
        """Test piece list normalization."""
        # Test with singular keys
        pieces_singular = {
            "King": ["e1"],
            "Queen": ["d1"],
            "Rook": ["a1", "h1"],  # Singular
            "Bishop": ["c1", "f1"],  # Singular
            "Knight": ["b1", "g1"],  # Singular
            "Pawn": ["a2", "b2"]  # Singular
        }
        
        normalized = position_validator._normalize_piece_list(pieces_singular)
        
        assert "Rooks" in normalized
        assert len(normalized["Rooks"]) == 2
        assert "Bishops" in normalized
        assert len(normalized["Bishops"]) == 2


class TestPositionExtractionIntegration:
    """Integration tests for position extraction and validation flow."""

    @pytest.mark.asyncio
    async def test_extract_and_validate_starting_position(
        self, position_extraction_agent, position_validator, starting_position_fen
    ):
        """Test full extraction and validation flow for starting position."""
        # Extract position
        extraction = await position_extraction_agent.extract_position(
            fen=starting_position_fen,
            last_move=None
        )
        
        # Validate extraction
        validation_result = position_validator.validate_extraction(
            extraction=extraction,
            fen=starting_position_fen
        )
        
        # Check results
        assert extraction is not None
        assert validation_result is not None
        # Note: Actual validation result depends on LLM accuracy
        # This test verifies the flow works, not perfect accuracy

    @pytest.mark.asyncio
    async def test_extract_with_error_feedback(
        self, position_extraction_agent, position_validator, starting_position_fen
    ):
        """Test extraction with error feedback (retry scenario)."""
        # First extraction
        extraction1 = await position_extraction_agent.extract_position(
            fen=starting_position_fen
        )
        
        # Validate and get discrepancies
        validation_result = position_validator.validate_extraction(
            extraction=extraction1,
            fen=starting_position_fen
        )
        
        # If validation failed, retry with error feedback
        if not validation_result.is_valid:
            error_feedback = "\n".join([
                f"- {disc}" for disc in validation_result.discrepancies[:5]
            ])
            
            extraction2 = await position_extraction_agent.extract_position(
                fen=starting_position_fen,
                error_feedback=error_feedback,
                corrected_pieces=validation_result.corrected_pieces
            )
            
            # Validate retry
            validation_result2 = position_validator.validate_extraction(
                extraction=extraction2,
                fen=starting_position_fen
            )
            
            assert extraction2 is not None
            assert validation_result2 is not None
            # Retry should ideally improve, but not guaranteed
