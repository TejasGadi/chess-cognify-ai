"""
Utility for generating chess board images from FEN positions.
Used for vision-based LLM analysis.
"""
import chess
import chess.svg
from typing import Optional
import base64
from io import BytesIO
from app.utils.logger import get_logger

logger = get_logger(__name__)


def fen_to_board_image_base64(
    fen: str,
    last_move: Optional[chess.Move] = None,
    size: int = 400,
    highlight_squares: Optional[list] = None
) -> str:
    """
    Convert FEN position to base64-encoded SVG image for vision models.
    
    Args:
        fen: FEN string representing the chess position
        last_move: Optional last move to highlight
        size: Board size in pixels
        highlight_squares: Optional list of squares to highlight (e.g., for best move)
    
    Returns:
        Base64-encoded SVG string (data URI format)
    """
    try:
        board = chess.Board(fen)
        
        # Generate SVG
        svg = chess.svg.board(
            board=board,
            lastmove=last_move,
            size=size,
            squares=highlight_squares if highlight_squares else None
        )
        
        # Convert to base64
        svg_bytes = svg.encode('utf-8')
        base64_svg = base64.b64encode(svg_bytes).decode('utf-8')
        
        # Return as data URI (compatible with vision models)
        return f"data:image/svg+xml;base64,{base64_svg}"
    
    except Exception as e:
        logger.error(f"Error generating board image from FEN: {e}")
        raise


def fen_to_board_image_url(
    fen: str,
    last_move: Optional[chess.Move] = None,
    size: int = 400
) -> dict:
    """
    Convert FEN position to image URL format for LangChain vision models.
    
    Args:
        fen: FEN string representing the chess position
        last_move: Optional last move to highlight
        size: Board size in pixels
    
    Returns:
        Dictionary with 'type' and 'image_url' keys for LangChain HumanMessage
    """
    base64_image = fen_to_board_image_base64(fen, last_move, size)
    
    return {
        "type": "image_url",
        "image_url": {"url": base64_image}
    }
