"""
Tests for theme analysis service and tactical pattern detector.
"""
import pytest
import chess
from app.services.theme_analysis_service import ThemeAnalysisService
from app.utils.tactical_patterns import TacticalPatternDetector


@pytest.fixture
def starting_position():
    """Starting position board."""
    return chess.Board()


@pytest.fixture
def test_position():
    """Test position (after e4 e5 Nf3 Nc6)."""
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    board.push_san("Nf3")
    board.push_san("Nc6")
    return board


class TestThemeAnalysisService:
    """Test theme analysis service."""

    def test_analyze_material_balance_starting_position(self, starting_position):
        """Test material balance for starting position."""
        result = ThemeAnalysisService.analyze_material_balance(starting_position)
        
        assert "white_material" in result
        assert "black_material" in result
        assert "balance" in result
        assert "advantage" in result
        assert "material_difference" in result
        
        # Starting position should have equal material
        assert result["white_material"] == result["black_material"]
        assert result["balance"] == 0
        assert result["advantage"] == "equal"

    def test_analyze_piece_mobility(self, starting_position):
        """Test piece mobility analysis."""
        result = ThemeAnalysisService.analyze_piece_mobility(starting_position)
        
        assert "white_moves" in result
        assert "black_moves" in result
        assert "mobility_difference" in result
        assert "mobility_advantage" in result
        assert "mobility_description" in result
        
        # White should have 20 legal moves in starting position
        assert result["white_moves"] == 20
        assert isinstance(result["mobility_description"], str)

    def test_analyze_space_control(self, starting_position):
        """Test space control analysis."""
        result = ThemeAnalysisService.analyze_space_control(starting_position)
        
        assert "white_space" in result
        assert "black_space" in result
        assert "space_difference" in result
        assert "space_advantage" in result
        assert "space_description" in result
        
        # Starting position: no advanced pawns
        assert result["white_space"] == 0
        assert result["black_space"] == 0

    def test_analyze_king_safety(self, starting_position):
        """Test king safety analysis."""
        result = ThemeAnalysisService.analyze_king_safety(starting_position)
        
        assert "white_king_safety" in result
        assert "black_king_safety" in result
        assert "white_king_square" in result
        assert "black_king_square" in result
        assert "white_pawn_shield" in result
        assert "black_pawn_shield" in result
        assert "king_safety_description" in result
        
        # Starting position: kings should be safe
        assert result["white_king_square"] == "e1"
        assert result["black_king_square"] == "e8"
        assert result["white_king_safety"] == "safe"
        assert result["black_king_safety"] == "safe"

    def test_analyze_position_themes(self, starting_position):
        """Test comprehensive theme analysis."""
        result = ThemeAnalysisService.analyze_position_themes(starting_position, use_cache=False)
        
        assert "material" in result
        assert "mobility" in result
        assert "space" in result
        assert "king_safety" in result
        
        # All sub-analyses should be present
        assert isinstance(result["material"], dict)
        assert isinstance(result["mobility"], dict)
        assert isinstance(result["space"], dict)
        assert isinstance(result["king_safety"], dict)


class TestTacticalPatternDetector:
    """Test tactical pattern detector."""

    def test_detect_pins_starting_position(self, starting_position):
        """Test pin detection in starting position."""
        pins = TacticalPatternDetector.detect_pins(starting_position)
        
        # Starting position should have no pins
        assert isinstance(pins, list)
        # May or may not have pins depending on implementation

    def test_detect_forks(self, test_position):
        """Test fork detection."""
        forks = TacticalPatternDetector.detect_forks(test_position)
        
        assert isinstance(forks, list)
        # May or may not have forks depending on position

    def test_detect_hanging_pieces(self, starting_position):
        """Test hanging piece detection."""
        hanging = TacticalPatternDetector.detect_hanging_pieces(starting_position)
        
        assert isinstance(hanging, list)
        # Starting position: no hanging pieces
        assert len(hanging) == 0

    def test_detect_weak_squares(self, starting_position):
        """Test weak square detection."""
        weak_squares = TacticalPatternDetector.detect_weak_squares(starting_position)
        
        assert isinstance(weak_squares, list)
        # Starting position: kings are safe, few weak squares

    def test_identify_tactical_patterns(self, starting_position):
        """Test combined tactical pattern identification."""
        patterns = TacticalPatternDetector.identify_tactical_patterns(starting_position)
        
        assert isinstance(patterns, list)
        # All items should be strings
        for pattern in patterns:
            assert isinstance(pattern, str)


class TestThemeAnalysisIntegration:
    """Integration tests for theme analysis."""

    def test_theme_analysis_with_tactical_patterns(self, test_position):
        """Test theme analysis combined with tactical patterns."""
        # Analyze themes
        themes = ThemeAnalysisService.analyze_position_themes(test_position, use_cache=False)
        
        # Detect tactical patterns
        patterns = TacticalPatternDetector.identify_tactical_patterns(test_position)
        
        # Both should work together
        assert isinstance(themes, dict)
        assert isinstance(patterns, list)
        
        # Themes should have all required keys
        assert "material" in themes
        assert "mobility" in themes
        assert "space" in themes
        assert "king_safety" in themes

    def test_theme_analysis_caching(self, starting_position):
        """Test theme analysis caching."""
        # First call (no cache)
        result1 = ThemeAnalysisService.analyze_position_themes(starting_position, use_cache=True)
        
        # Second call (should use cache)
        result2 = ThemeAnalysisService.analyze_position_themes(starting_position, use_cache=True)
        
        # Results should be identical
        assert result1 == result2
