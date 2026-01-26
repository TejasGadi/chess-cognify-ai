"""
PGN (Portable Game Notation) processing service.
"""
import chess
import chess.pgn
from typing import Optional, Dict, Any, List, Tuple
from io import StringIO
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PGNService:
    """Service for parsing and processing PGN files."""

    @staticmethod
    def parse_pgn(pgn_string: str) -> Optional[chess.pgn.Game]:
        """
        Parse a PGN string into a chess.pgn.Game object.

        Args:
            pgn_string: PGN format string

        Returns:
            chess.pgn.Game object or None if parsing fails
        """
        try:
            pgn_io = StringIO(pgn_string)
            game = chess.pgn.read_game(pgn_io)
            return game
        except Exception as e:
            logger.error(f"Error parsing PGN: {e}")
            return None

    @staticmethod
    def validate_pgn(pgn_string: str) -> Tuple[bool, Optional[str]]:
        """
        Validate PGN format and structure.

        Args:
            pgn_string: PGN format string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not pgn_string or not pgn_string.strip():
            return False, "PGN string is empty"

        try:
            game = PGNService.parse_pgn(pgn_string)
            if game is None:
                return False, "Failed to parse PGN"

            # Check if game has moves
            if game.end() is None:
                return False, "PGN contains no moves"

            # Try to replay the game to validate moves
            board = game.board()
            for move in game.mainline_moves():
                if move not in board.legal_moves:
                    return False, f"Invalid move in PGN: {move}"
                board.push(move)

            return True, None
        except Exception as e:
            return False, f"PGN validation error: {str(e)}"

    @staticmethod
    def extract_metadata(game: chess.pgn.Game) -> Dict[str, Any]:
        """
        Extract metadata from a PGN game.

        Args:
            game: chess.pgn.Game object

        Returns:
            Dictionary with metadata:
            {
                "white": str,
                "black": str,
                "result": str,
                "event": str,
                "site": str,
                "date": str,
                "round": str,
                "time_control": str,
                "eco": str,  # Opening code
            }
        """
        headers = game.headers
        return {
            "white": headers.get("White", "Unknown"),
            "black": headers.get("Black", "Unknown"),
            "result": headers.get("Result", "*"),
            "event": headers.get("Event", ""),
            "site": headers.get("Site", ""),
            "date": headers.get("Date", ""),
            "round": headers.get("Round", ""),
            "time_control": headers.get("TimeControl", ""),
            "eco": headers.get("ECO", ""),  # Encyclopedia of Chess Openings
        }

    @staticmethod
    def extract_move_sequence(game: chess.pgn.Game) -> List[Dict[str, Any]]:
        """
        Extract move sequence from PGN game.

        Args:
            game: chess.pgn.Game object

        Returns:
            List of move dictionaries:
            [
                {
                    "ply": int,  # Half-move number (1, 2, 3, ...)
                    "move": str,  # UCI format
                    "move_san": str,  # Standard Algebraic Notation
                    "fen": str,  # FEN after move
                },
                ...
            ]
        """
        moves = []
        board = game.board()
        ply = 0

        for move in game.mainline_moves():
            ply += 1
            move_uci = move.uci()
            move_san = board.san(move)
            board.push(move)
            fen = board.fen()

            moves.append(
                {
                    "ply": ply,
                    "move": move_uci,
                    "move_san": move_san,
                    "fen": fen,
                }
            )

        return moves

    @staticmethod
    def get_position_before_move(
        game: chess.pgn.Game, ply: int
    ) -> Optional[chess.Board]:
        """
        Get the board position before a specific move (by ply number).

        Args:
            game: chess.pgn.Game object
            ply: Half-move number (1-indexed)

        Returns:
            chess.Board object or None if ply is invalid
        """
        if ply < 1:
            return None

        board = game.board()
        move_count = 0

        for move in game.mainline_moves():
            move_count += 1
            if move_count == ply:
                return board.copy()
            board.push(move)

        return None

    @staticmethod
    def get_position_after_move(
        game: chess.pgn.Game, ply: int
    ) -> Optional[chess.Board]:
        """
        Get the board position after a specific move (by ply number).

        Args:
            game: chess.pgn.Game object
            ply: Half-move number (1-indexed)

        Returns:
            chess.Board object or None if ply is invalid
        """
        if ply < 1:
            return None

        board = game.board()
        move_count = 0

        for move in game.mainline_moves():
            move_count += 1
            board.push(move)
            if move_count == ply:
                return board.copy()

        return None

    @staticmethod
    def get_move_at_ply(game: chess.pgn.Game, ply: int) -> Optional[chess.Move]:
        """
        Get the move at a specific ply number.

        Args:
            game: chess.pgn.Game object
            ply: Half-move number (1-indexed)

        Returns:
            chess.Move object or None if ply is invalid
        """
        if ply < 1:
            return None

        move_count = 0
        for move in game.mainline_moves():
            move_count += 1
            if move_count == ply:
                return move

        return None

    @staticmethod
    def get_total_plies(game: chess.pgn.Game) -> int:
        """
        Get total number of half-moves (plies) in the game.

        Args:
            game: chess.pgn.Game object

        Returns:
            Total number of plies
        """
        return sum(1 for _ in game.mainline_moves())

    @staticmethod
    def detect_game_phase(ply: int, total_plies: int, board: chess.Board) -> str:
        """
        Detect game phase (opening, middlegame, endgame).

        Args:
            ply: Current half-move number
            total_plies: Total plies in game
            board: Current board position

        Returns:
            Phase string: "opening", "middlegame", or "endgame"
        """
        # Opening: first 12 moves (24 plies)
        if ply <= 24:
            return "opening"

        # Endgame: few pieces remaining
        # Count non-pawn pieces
        non_pawn_pieces = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(
            board.pieces(chess.QUEEN, chess.BLACK)
        )
        non_pawn_pieces += len(board.pieces(chess.ROOK, chess.WHITE)) + len(
            board.pieces(chess.ROOK, chess.BLACK)
        )
        non_pawn_pieces += len(board.pieces(chess.BISHOP, chess.WHITE)) + len(
            board.pieces(chess.BISHOP, chess.BLACK)
        )
        non_pawn_pieces += len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(
            board.pieces(chess.KNIGHT, chess.BLACK)
        )

        # Endgame: 6 or fewer non-pawn pieces
        if non_pawn_pieces <= 6:
            return "endgame"

        return "middlegame"
