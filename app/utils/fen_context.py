"""
Temporary FEN context store for agent analysis.
Stores current position state during move analysis to prevent hallucination.
"""
from typing import Optional, Dict, Any
from app.utils.logger import get_logger
import threading

logger = get_logger(__name__)


class FENContext:
    """
    Thread-local context store for FEN positions during analysis.
    Each analysis session gets its own context that's cleared after use.
    """
    
    def __init__(self):
        """Initialize FEN context with thread-local storage."""
        self._local = threading.local()
    
    def set_context(
        self,
        fen_before: str,
        fen_after: str,
        played_move: str,
        best_move: str,
        played_move_san: str,
        best_move_san: str,
    ) -> None:
        """
        Set the current analysis context.
        
        Args:
            fen_before: FEN position before the move
            fen_after: FEN position after the move
            played_move: Played move in UCI format
            best_move: Best move in UCI format
            played_move_san: Played move in SAN format
            best_move_san: Best move in SAN format
        """
        self._local.context = {
            "fen_before": fen_before,
            "fen_after": fen_after,
            "played_move": played_move,
            "best_move": best_move,
            "played_move_san": played_move_san,
            "best_move_san": best_move_san,
        }
        logger.debug(f"FEN context set: fen_before={fen_before[:50]}..., fen_after={fen_after[:50]}...")
    
    def get_context(self) -> Optional[Dict[str, Any]]:
        """Get the current analysis context."""
        return getattr(self._local, 'context', None)
    
    def get_fen_before(self) -> Optional[str]:
        """Get FEN position before the move."""
        context = self.get_context()
        return context.get("fen_before") if context else None
    
    def get_fen_after(self) -> Optional[str]:
        """Get FEN position after the move."""
        context = self.get_context()
        return context.get("fen_after") if context else None
    
    def get_played_move(self) -> Optional[str]:
        """Get played move in UCI format."""
        context = self.get_context()
        return context.get("played_move") if context else None
    
    def get_best_move(self) -> Optional[str]:
        """Get best move in UCI format."""
        context = self.get_context()
        return context.get("best_move") if context else None
    
    def clear(self) -> None:
        """Clear the current context."""
        if hasattr(self._local, 'context'):
            delattr(self._local, 'context')
        logger.debug("FEN context cleared")


# Global FEN context instance
fen_context = FENContext()
