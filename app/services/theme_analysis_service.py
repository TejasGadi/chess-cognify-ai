"""
Theme Analysis Service - Calculates structured positional insights.
Provides material, mobility, space, king safety, and tactical pattern analysis.
Includes caching for performance optimization.
"""
from typing import Dict, Any, List, Optional
import chess
from app.utils.logger import get_logger
from app.utils.cache import get_from_cache, set_to_cache

logger = get_logger(__name__)

# Standard piece values (in pawns)
PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}


class ThemeAnalysisService:
    """Service for analyzing chess position themes."""

    @staticmethod
    def analyze_material_balance(board: chess.Board) -> Dict[str, Any]:
        """
        Analyze material balance between White and Black.

        Args:
            board: chess.Board object

        Returns:
            Dictionary with material analysis:
            {
                "white_material": int,
                "black_material": int,
                "balance": int,  # white - black (in pawns)
                "advantage": str,  # "white", "black", or "equal"
                "material_difference": str  # Human-readable description
            }
        """
        white_material = 0
        black_material = 0

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = PIECE_VALUES.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    white_material += value
                else:
                    black_material += value

        balance = white_material - black_material

        if balance > 1:
            advantage = "white"
            material_difference = f"White has +{balance} pawn advantage"
        elif balance < -1:
            advantage = "black"
            material_difference = f"Black has +{abs(balance)} pawn advantage"
        else:
            advantage = "equal"
            if balance == 0:
                material_difference = "Material is equal"
            elif balance == 1:
                material_difference = "White has +1 pawn advantage"
            else:
                material_difference = "Black has +1 pawn advantage"

        return {
            "white_material": white_material,
            "black_material": black_material,
            "balance": balance,
            "advantage": advantage,
            "material_difference": material_difference,
        }

    @staticmethod
    def analyze_piece_mobility(board: chess.Board) -> Dict[str, Any]:
        """
        Analyze piece mobility (number of legal moves) for each side.

        Args:
            board: chess.Board object

        Returns:
            Dictionary with mobility analysis:
            {
                "white_moves": int,
                "black_moves": int,
                "mobility_difference": int,  # white - black
                "mobility_advantage": str,  # "white", "black", or "equal"
                "mobility_description": str  # Human-readable description
            }
        """
        white_moves = len(list(board.legal_moves))
        
        # Switch to black's turn to count black moves
        board_copy = board.copy()
        board_copy.turn = chess.BLACK
        black_moves = len(list(board_copy.legal_moves))

        mobility_difference = white_moves - black_moves

        if mobility_difference > 3:
            mobility_advantage = "white"
            mobility_description = f"White has {mobility_difference} more moves ({white_moves} vs {black_moves})"
        elif mobility_difference < -3:
            mobility_advantage = "black"
            mobility_description = f"Black has {abs(mobility_difference)} more moves ({black_moves} vs {white_moves})"
        else:
            mobility_advantage = "equal"
            if mobility_difference == 0:
                mobility_description = f"Mobility is equal ({white_moves} moves each)"
            elif mobility_difference > 0:
                mobility_description = f"White has slight mobility advantage ({white_moves} vs {black_moves} moves)"
            else:
                mobility_description = f"Black has slight mobility advantage ({black_moves} vs {white_moves} moves)"

        return {
            "white_moves": white_moves,
            "black_moves": black_moves,
            "mobility_difference": mobility_difference,
            "mobility_advantage": mobility_advantage,
            "mobility_description": mobility_description,
        }

    @staticmethod
    def analyze_space_control(board: chess.Board) -> Dict[str, Any]:
        """
        Analyze space control (squares controlled by pawns).

        Args:
            board: chess.Board object

        Returns:
            Dictionary with space analysis:
            {
                "white_space": int,  # Pawns on ranks 4-6
                "black_space": int,  # Pawns on ranks 3-5
                "space_difference": int,
                "space_advantage": str,
                "space_description": str
            }
        """
        white_space = 0
        black_space = 0

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(square)
                if piece.color == chess.WHITE:
                    # White pawns on ranks 4-6 (0-indexed: 3-5) control space
                    if rank >= 3:
                        white_space += 1
                else:
                    # Black pawns on ranks 3-5 (0-indexed: 2-4) control space
                    if rank <= 4:
                        black_space += 1

        space_difference = white_space - black_space

        if space_difference > 2:
            space_advantage = "white"
            space_description = f"White controls more space ({white_space} advanced pawns vs {black_space})"
        elif space_difference < -2:
            space_advantage = "black"
            space_description = f"Black controls more space ({black_space} advanced pawns vs {white_space})"
        else:
            space_advantage = "equal"
            space_description = f"Space control is roughly equal (White: {white_space}, Black: {black_space} advanced pawns)"

        return {
            "white_space": white_space,
            "black_space": black_space,
            "space_difference": space_difference,
            "space_advantage": space_advantage,
            "space_description": space_description,
        }

    @staticmethod
    def analyze_king_safety(board: chess.Board) -> Dict[str, Any]:
        """
        Analyze king safety for both sides.

        Args:
            board: chess.Board object

        Returns:
            Dictionary with king safety analysis:
            {
                "white_king_safety": str,  # "safe", "vulnerable", "exposed"
                "black_king_safety": str,
                "white_king_square": str,
                "black_king_square": str,
                "white_pawn_shield": int,  # Pawns around king
                "black_pawn_shield": int,
                "white_open_files": List[str],  # Open files near king
                "black_open_files": List[str],
                "king_safety_description": str
            }
        """
        # Find king squares
        white_king_square = board.king(chess.WHITE)
        black_king_square = board.king(chess.BLACK)

        white_king_square_name = chess.square_name(white_king_square) if white_king_square is not None else None
        black_king_square_name = chess.square_name(black_king_square) if black_king_square is not None else None

        # Count pawn shield (pawns on adjacent files and ranks)
        white_pawn_shield = ThemeAnalysisService._count_pawn_shield(board, white_king_square, chess.WHITE)
        black_pawn_shield = ThemeAnalysisService._count_pawn_shield(board, black_king_square, chess.BLACK)

        # Find open files near kings
        white_open_files = ThemeAnalysisService._find_open_files_near_king(board, white_king_square, chess.WHITE)
        black_open_files = ThemeAnalysisService._find_open_files_near_king(board, black_king_square, chess.BLACK)

        # Assess king safety
        white_safety = ThemeAnalysisService._assess_king_safety(white_pawn_shield, len(white_open_files))
        black_safety = ThemeAnalysisService._assess_king_safety(black_pawn_shield, len(black_open_files))

        # Build description
        safety_descriptions = []
        if white_safety == "exposed":
            safety_descriptions.append(f"White's king on {white_king_square_name} is exposed (weak pawn shield, open files: {', '.join(white_open_files) if white_open_files else 'none'})")
        elif white_safety == "vulnerable":
            safety_descriptions.append(f"White's king on {white_king_square_name} is vulnerable")
        
        if black_safety == "exposed":
            safety_descriptions.append(f"Black's king on {black_king_square_name} is exposed (weak pawn shield, open files: {', '.join(black_open_files) if black_open_files else 'none'})")
        elif black_safety == "vulnerable":
            safety_descriptions.append(f"Black's king on {black_king_square_name} is vulnerable")

        if not safety_descriptions:
            safety_descriptions.append("Both kings are relatively safe")

        return {
            "white_king_safety": white_safety,
            "black_king_safety": black_safety,
            "white_king_square": white_king_square_name,
            "black_king_square": black_king_square_name,
            "white_pawn_shield": white_pawn_shield,
            "black_pawn_shield": black_pawn_shield,
            "white_open_files": white_open_files,
            "black_open_files": black_open_files,
            "king_safety_description": "; ".join(safety_descriptions),
        }

    @staticmethod
    def _count_pawn_shield(board: chess.Board, king_square: int, color: bool) -> int:
        """Count pawns protecting the king."""
        if king_square is None:
            return 0

        king_rank = chess.square_rank(king_square)
        king_file = chess.square_file(king_square)
        
        shield_count = 0
        
        # Check pawns on ranks in front of king (1-2 ranks ahead)
        for rank_offset in [1, 2]:
            check_rank = king_rank + (1 if color == chess.WHITE else -1) * rank_offset
            if 0 <= check_rank <= 7:
                # Check adjacent files
                for file_offset in [-1, 0, 1]:
                    check_file = king_file + file_offset
                    if 0 <= check_file <= 7:
                        square = chess.square(check_file, check_rank)
                        piece = board.piece_at(square)
                        if piece and piece.piece_type == chess.PAWN and piece.color == color:
                            shield_count += 1
        
        return shield_count

    @staticmethod
    def _find_open_files_near_king(board: chess.Board, king_square: int, color: bool) -> List[str]:
        """Find open files near the king."""
        if king_square is None:
            return []

        king_file = chess.square_file(king_square)
        open_files = []
        
        # Check files adjacent to king (±1 file)
        for file_offset in [-1, 0, 1]:
            check_file = king_file + file_offset
            if 0 <= check_file <= 7:
                file_name = chr(ord('a') + check_file)
                # Check if file is open (no pawns of either color)
                has_white_pawn = False
                has_black_pawn = False
                for rank in range(8):
                    square = chess.square(check_file, rank)
                    piece = board.piece_at(square)
                    if piece and piece.piece_type == chess.PAWN:
                        if piece.color == chess.WHITE:
                            has_white_pawn = True
                        else:
                            has_black_pawn = True
                
                if not has_white_pawn and not has_black_pawn:
                    open_files.append(file_name)
        
        return open_files

    @staticmethod
    def _assess_king_safety(pawn_shield: int, open_files: int) -> str:
        """Assess king safety based on pawn shield and open files."""
        if pawn_shield <= 1 and open_files >= 2:
            return "exposed"
        elif pawn_shield <= 2 or open_files >= 1:
            return "vulnerable"
        else:
            return "safe"

    @staticmethod
    def analyze_position_themes(
        board: chess.Board, 
        use_cache: bool = True,
        cache_ttl: int = 86400  # 24 hours
    ) -> Dict[str, Any]:
        """
        Analyze all positional themes for a position.
        Uses caching to avoid recalculation for the same position.

        Args:
            board: chess.Board object
            use_cache: Whether to use cached results
            cache_ttl: Cache TTL in seconds (default: 24 hours)

        Returns:
            Comprehensive theme analysis dictionary
        """
        fen = board.fen()
        cache_key = f"theme:{fen}"
        
        # Check cache first
        if use_cache:
            cached = get_from_cache(cache_key)
            if cached:
                logger.debug(f"Using cached theme analysis for position")
                return cached
        
        logger.debug("Analyzing position themes")
        
        material = ThemeAnalysisService.analyze_material_balance(board)
        mobility = ThemeAnalysisService.analyze_piece_mobility(board)
        space = ThemeAnalysisService.analyze_space_control(board)
        king_safety = ThemeAnalysisService.analyze_king_safety(board)

        result = {
            "material": material,
            "mobility": mobility,
            "space": space,
            "king_safety": king_safety,
        }
        
        # Cache result
        if use_cache:
            set_to_cache(cache_key, result, ttl=cache_ttl)
            logger.debug(f"Cached theme analysis for position")
        
        return result
