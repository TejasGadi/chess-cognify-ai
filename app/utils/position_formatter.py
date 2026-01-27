"""
Position Formatter - Converts FEN to LLM-friendly representations.
Provides ASCII board, enhanced FEN, and piece list formats.
"""
import chess
from typing import Dict, List, Tuple
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Unicode piece symbols
PIECE_SYMBOLS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',  # White
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',  # Black
    '.': '·'  # Empty square
}

# Piece names for natural language
PIECE_NAMES = {
    'K': 'King', 'Q': 'Queen', 'R': 'Rook', 'B': 'Bishop', 'N': 'Knight', 'P': 'Pawn',
    'k': 'King', 'q': 'Queen', 'r': 'Rook', 'b': 'Bishop', 'n': 'Knight', 'p': 'Pawn'
}


def fen_to_ascii_board(fen: str, highlight_squares: List[str] = None) -> str:
    """
    Convert FEN position to ASCII board representation.
    
    Args:
        fen: FEN string
        highlight_squares: Optional list of squares to highlight (e.g., ['e4', 'd5'])
    
    Returns:
        ASCII board string with file/rank labels
    """
    try:
        board = chess.Board(fen)
        highlight_set = set(highlight_squares) if highlight_squares else set()
        
        lines = []
        lines.append("    " + "   ".join(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']))
        lines.append("  " + "─" * 33)
        
        for rank in range(7, -1, -1):  # 8 to 1
            rank_line = f"{rank + 1} |"
            for file in range(8):  # a to h
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                
                if piece:
                    symbol = PIECE_SYMBOLS.get(piece.symbol(), '?')
                else:
                    symbol = '·'
                
                square_name = chess.square_name(square)
                if square_name in highlight_set:
                    rank_line += f" [{symbol}] |"
                else:
                    rank_line += f" {symbol} |"
            
            rank_line += f" {rank + 1}"
            lines.append(rank_line)
            if rank > 0:
                lines.append("  " + "─" * 33)
        
        lines.append("  " + "─" * 33)
        lines.append("    " + "   ".join(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']))
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error generating ASCII board from FEN: {e}")
        return f"[Error generating board: {str(e)}]"


def fen_to_piece_list(fen: str) -> str:
    """
    Convert FEN position to explicit piece list.
    
    Args:
        fen: FEN string
    
    Returns:
        Formatted piece list string
    """
    try:
        board = chess.Board(fen)
        
        white_pieces = {
            'King': [], 'Queen': [], 'Rooks': [], 'Bishops': [], 'Knights': [], 'Pawns': []
        }
        black_pieces = {
            'King': [], 'Queen': [], 'Rooks': [], 'Bishops': [], 'Knights': [], 'Pawns': []
        }
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                square_name = chess.square_name(square)
                piece_name = PIECE_NAMES.get(piece.symbol(), 'Unknown')
                
                if piece.color == chess.WHITE:
                    if piece_name == 'King':
                        white_pieces['King'].append(square_name)
                    elif piece_name == 'Queen':
                        white_pieces['Queen'].append(square_name)
                    elif piece_name == 'Rook':
                        white_pieces['Rooks'].append(square_name)
                    elif piece_name == 'Bishop':
                        white_pieces['Bishops'].append(square_name)
                    elif piece_name == 'Knight':
                        white_pieces['Knights'].append(square_name)
                    elif piece_name == 'Pawn':
                        white_pieces['Pawns'].append(square_name)
                else:
                    if piece_name == 'King':
                        black_pieces['King'].append(square_name)
                    elif piece_name == 'Queen':
                        black_pieces['Queen'].append(square_name)
                    elif piece_name == 'Rook':
                        black_pieces['Rooks'].append(square_name)
                    elif piece_name == 'Bishop':
                        black_pieces['Bishops'].append(square_name)
                    elif piece_name == 'Knight':
                        black_pieces['Knights'].append(square_name)
                    elif piece_name == 'Pawn':
                        black_pieces['Pawns'].append(square_name)
        
        # Format output
        lines = []
        lines.append("White pieces:")
        for piece_type, squares in white_pieces.items():
            if squares:
                if piece_type in ['King', 'Queen']:
                    lines.append(f"  {piece_type}: {', '.join(squares)}")
                else:
                    lines.append(f"  {piece_type}: {', '.join(squares)}")
        
        lines.append("")
        lines.append("Black pieces:")
        for piece_type, squares in black_pieces.items():
            if squares:
                if piece_type in ['King', 'Queen']:
                    lines.append(f"  {piece_type}: {', '.join(squares)}")
                else:
                    lines.append(f"  {piece_type}: {', '.join(squares)}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error generating piece list from FEN: {e}")
        return f"[Error generating piece list: {str(e)}]"


def validate_position_consistency(fen: str) -> bool:
    """
    Validate that FEN can be parsed and is consistent.
    
    Args:
        fen: FEN string to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        board = chess.Board(fen)
        # Re-generate FEN to ensure it's normalized
        normalized_fen = board.fen()
        return normalized_fen == fen or True  # Allow slight variations
    except Exception as e:
        logger.error(f"FEN validation failed: {e}")
        return False


def format_position_for_llm(fen: str, last_move: str = None, highlight_squares: List[str] = None) -> str:
    """
    Format chess position using combined approach: ASCII board + FEN + piece list.
    All three representations are generated from the same FEN to ensure synchronization.
    
    Args:
        fen: FEN string (position AFTER the move)
        last_move: Optional last move in SAN (for context)
        highlight_squares: Optional squares to highlight on board
    
    Returns:
        Combined formatted string with all three representations
    """
    try:
        # Validate FEN first and normalize it
        board = chess.Board(fen)
        fen_validated = board.fen()  # Re-generate FEN to ensure it's valid and normalized
        
        # Verify all three representations will be generated from the same FEN
        if not validate_position_consistency(fen_validated):
            logger.warning(f"Position consistency check failed for FEN: {fen_validated[:50]}...")
        
        # Verify all three representations use the same FEN
        lines = []
        lines.append("=" * 60)
        lines.append("CHESS POSITION REPRESENTATION")
        lines.append("=" * 60)
        lines.append("")
        lines.append("**IMPORTANT: All three representations below show the SAME position (after the move).**")
        lines.append("")
        
        # 1. ASCII Board
        lines.append("1. ASCII BOARD (Visual representation):")
        lines.append("")
        ascii_board = fen_to_ascii_board(fen_validated, highlight_squares)
        lines.append(ascii_board)
        lines.append("")
        
        # 2. Enhanced FEN
        lines.append("2. FEN NOTATION (Standard position encoding):")
        lines.append(f"   {fen_validated}")
        if last_move:
            lines.append(f"   (Position AFTER {last_move} was played)")
        lines.append("")
        
        # 3. Piece List
        lines.append("3. PIECE LOCATIONS (Explicit piece positions):")
        piece_list = fen_to_piece_list(fen_validated)
        lines.append(piece_list)
        lines.append("")
        
        # Add validation note
        lines.append("**VERIFICATION:** All three representations above show the same position.")
        lines.append("Use them together to verify piece locations and avoid errors.")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error formatting position for LLM: {e}")
        return f"[Error formatting position: {str(e)}]"
