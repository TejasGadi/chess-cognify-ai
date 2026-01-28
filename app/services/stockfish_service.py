"""
Stockfish engine service wrapper for UCI protocol communication.
"""
import chess
import chess.engine
from typing import Optional, Dict, Any, List
import asyncio
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockfishService:
    """Wrapper for Stockfish engine using python-chess UCI interface."""

    def __init__(self):
        """Initialize Stockfish service with configuration."""
        # Auto-detect Stockfish if configured path doesn't exist
        import os
        import shutil
        
        stockfish_path = settings.stockfish_path
        if not os.path.exists(stockfish_path):
            # Try to find Stockfish in common locations
            detected_path = shutil.which("stockfish")
            if detected_path:
                stockfish_path = detected_path
                logger.info(f"Stockfish not found at {settings.stockfish_path}, using detected path: {stockfish_path}")
            else:
                logger.error(f"Stockfish not found at {settings.stockfish_path} and not in PATH")
                raise FileNotFoundError(
                    f"Stockfish not found. Please install Stockfish or set STOCKFISH_PATH in .env. "
                    f"Tried: {settings.stockfish_path}"
                )
        
        self.stockfish_path = stockfish_path
        self.depth = settings.stockfish_depth
        self.threads = settings.stockfish_threads
        self.hash_size = settings.stockfish_hash
        self.timeout = settings.stockfish_timeout
        self._engine: Optional[chess.engine.SimpleEngine] = None

    async def _get_engine(self) -> chess.engine.SimpleEngine:
        """Get or create engine instance."""
        if self._engine is None:
            try:
                transport, engine = await chess.engine.popen_uci(
                    self.stockfish_path,
                )
                # Configure engine
                await engine.configure(
                    {
                        "Threads": self.threads,
                        "Hash": self.hash_size,
                    }
                )
                self._engine = engine
                logger.info(
                    f"Stockfish engine initialized: depth={self.depth}, "
                    f"threads={self.threads}, hash={self.hash_size}MB"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Stockfish engine: {e}")
                raise
        return self._engine

    async def evaluate_position(
        self, board: chess.Board, depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a chess position.

        Args:
            board: chess.Board object representing the position
            depth: Analysis depth (uses default if None)

        Returns:
            Dictionary with evaluation info:
            {
                "score": float,  # Centipawns (positive = white advantage)
                "score_str": str,  # Human-readable (e.g., "+0.4")
                "depth": int,
                "pv": list[str],  # Principal variation (best line)
            }
        """
        engine = await self._get_engine()
        analysis_depth = depth or self.depth

        try:
            # Analyze position with timeout
            info = await asyncio.wait_for(
                engine.analyse(board, chess.engine.Limit(depth=analysis_depth)),
                timeout=self.timeout,
            )

            # Extract score
            score = info.get("score")
            if score is None:
                raise ValueError("Engine returned no score")

            # Convert score to centipawns
            # python-chess 1.0+ uses PovScore with .white()/.black() methods
            # .white() returns a Cp object, which has .score() to get the integer value
            if score.is_mate():
                # Mate score: convert to large centipawn value
                mate_score = score.white().mate()
                centipawns = 10000 if mate_score > 0 else -10000
                score_str = f"M{mate_score}" if mate_score else "M0"
            else:
                # Normal score in centipawns
                # Use .white().score() to get centipawns as integer from white's perspective
                # This works for python-chess 1.0+
                centipawns = score.white().score()
                # Convert to pawns for display
                pawns = centipawns / 100.0
                score_str = f"{pawns:+.2f}"

            # Get principal variation (best line)
            # PV moves need to be converted to SAN by applying them sequentially
            pv = info.get("pv", [])
            pv_moves = []
            if pv:
                pv_board = board.copy()
                for move in pv:
                    try:
                        if move in pv_board.legal_moves:
                            pv_moves.append(pv_board.san(move))
                            pv_board.push(move)
                        else:
                            # If move is not legal, use UCI notation as fallback
                            pv_moves.append(move.uci())
                            logger.warning(f"PV move {move.uci()} not legal in position, using UCI")
                    except Exception as e:
                        # Fallback to UCI if SAN conversion fails
                        pv_moves.append(move.uci())
                        logger.warning(f"Error converting PV move to SAN: {e}, using UCI: {move.uci()}")

            return {
                "score": centipawns,
                "score_str": score_str,
                "depth": info.get("depth", analysis_depth),
                "pv": pv_moves,
            }
        except asyncio.TimeoutError:
            logger.warning(f"Stockfish analysis timed out after {self.timeout}s")
            raise TimeoutError(f"Engine analysis exceeded timeout of {self.timeout}s")
        except Exception as e:
            logger.error(f"Error evaluating position: {e}")
            raise

    async def get_best_move(
        self, board: chess.Board, depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get the best move for a position.

        Args:
            board: chess.Board object representing the position
            depth: Analysis depth (uses default if None)

        Returns:
            Dictionary with best move info:
            {
                "move": str,  # UCI format (e.g., "e2e4")
                "move_san": str,  # Standard Algebraic Notation (e.g., "e4")
                "eval": float,  # Evaluation after best move
                "eval_str": str,  # Human-readable evaluation
            }
        """
        engine = await self._get_engine()
        analysis_depth = depth or self.depth

        try:
            # Get best move
            result = await asyncio.wait_for(
                engine.play(board, chess.engine.Limit(depth=analysis_depth)),
                timeout=self.timeout,
            )

            best_move = result.move
            move_uci = best_move.uci()
            # Ensure move is legal before converting to SAN
            if best_move in board.legal_moves:
                move_san = board.san(best_move)
            else:
                # Fallback to UCI if move is not legal (shouldn't happen, but safety check)
                move_san = move_uci
                logger.warning(f"Best move {move_uci} not legal in position, using UCI notation")

            # Evaluate position after best move
            board_copy = board.copy()
            board_copy.push(best_move)
            eval_info = await self.evaluate_position(board_copy, analysis_depth)

            return {
                "move": move_uci,
                "move_san": move_san,
                "eval": eval_info["score"],
                "eval_str": eval_info["score_str"],
            }
        except asyncio.TimeoutError:
            logger.warning(f"Stockfish best move calculation timed out")
            raise TimeoutError(f"Engine analysis exceeded timeout of {self.timeout}s")
        except Exception as e:
            logger.error(f"Error getting best move: {e}")
            raise

    async def get_top_moves(
        self, board: chess.Board, top_n: int = 5, depth: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top N moves for a position with their evaluations.

        Args:
            board: chess.Board object representing the position
            top_n: Number of top moves to return (default: 5)
            depth: Analysis depth (uses default if None)

        Returns:
            List of dictionaries with move info:
            [
                {
                    "move": str,  # UCI format
                    "move_san": str,  # SAN notation
                    "eval": float,  # Centipawns
                    "eval_str": str,  # Human-readable
                    "rank": int,  # 1 = best, 2 = second best, etc.
                },
                ...
            ]
        """
        engine = await self._get_engine()
        analysis_depth = depth or self.depth

        try:
            # Use analyse with multipv parameter directly (not via configure)
            # When multipv > 1, analyse returns a list of info dicts
            info = await asyncio.wait_for(
                engine.analyse(board, chess.engine.Limit(depth=analysis_depth), multipv=top_n),
                timeout=self.timeout,
            )

            top_moves = []
            
            # When multipv > 1, analyse returns a list of info dicts
            # Each dict represents one of the top moves
            if isinstance(info, list):
                for idx, move_info in enumerate(info[:top_n]):
                    score = move_info.get("score")
                    pv = move_info.get("pv", [])
                    
                    if score is None or not pv:
                        continue
                    
                    move = pv[0]  # First move in principal variation
                    move_uci = move.uci()
                    
                    # Convert to SAN
                    try:
                        if move in board.legal_moves:
                            move_san = board.san(move)
                        else:
                            move_san = move_uci
                    except:
                        move_san = move_uci
                    
                    # Get evaluation
                    if score.is_mate():
                        mate_score = score.white().mate()
                        centipawns = 10000 if mate_score > 0 else -10000
                        eval_str = f"M{mate_score}" if mate_score else "M0"
                    else:
                        centipawns = score.white().score()
                        pawns = centipawns / 100.0
                        eval_str = f"{pawns:+.2f}"
                    
                    # Get PV moves in SAN
                    pv_moves_san = []
                    pv_board = board.copy()
                    for m in pv:
                        try:
                            if m in pv_board.legal_moves:
                                pv_moves_san.append(pv_board.san(m))
                                pv_board.push(m)
                            else:
                                pv_moves_san.append(m.uci())
                        except:
                            pv_moves_san.append(m.uci())

                    top_moves.append({
                        "move": move_uci,
                        "move_san": move_san,
                        "eval": centipawns,
                        "eval_str": eval_str,
                        "rank": idx + 1,
                        "pv_san": pv_moves_san,
                    })
            else:
                # Fallback: single analysis result (multipv might not be supported or only 1 move)
                pv = info.get("pv", [])
                if pv:
                    move = pv[0]
                    move_uci = move.uci()
                    try:
                        move_san = board.san(move) if move in board.legal_moves else move_uci
                    except:
                        move_san = move_uci
                    score = info.get("score")
                    
                    if score:
                        if score.is_mate():
                            mate_score = score.white().mate()
                            centipawns = 10000 if mate_score > 0 else -10000
                            eval_str = f"M{mate_score}" if mate_score else "M0"
                        else:
                            centipawns = score.white().score()
                            pawns = centipawns / 100.0
                            eval_str = f"{pawns:+.2f}"
                        
                        top_moves.append({
                            "move": move_uci,
                            "move_san": move_san,
                            "eval": centipawns,
                            "eval_str": eval_str,
                            "rank": 1,
                        })

            return top_moves
        except asyncio.TimeoutError:
            logger.warning(f"Top moves analysis timed out after {self.timeout}s")
            raise TimeoutError(f"Engine analysis exceeded timeout of {self.timeout}s")
        except Exception as e:
            logger.error(f"Error getting top moves: {e}")
            raise

    async def analyze_move(
        self, board: chess.Board, move: chess.Move, depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze a specific move in a position with top 5 alternative moves.

        Args:
            board: chess.Board object representing the position before move
            move: chess.Move to analyze
            depth: Analysis depth (uses default if None)

        Returns:
            Dictionary with move analysis:
            {
                "eval_before": float,
                "eval_before_str": str,
                "eval_after": float,
                "eval_after_str": str,
                "best_move": str,  # UCI format
                "best_move_san": str,
                "eval_best": float,
                "eval_best_str": str,
                "top_moves": [  # Top 5 moves with evaluations
                    {
                        "move": str,
                        "move_san": str,
                        "eval": float,
                        "eval_str": str,
                        "rank": int,
                    },
                    ...
                ],
                "played_move_eval": float,  # Evaluation of the played move
                "played_move_eval_str": str,
            }
        """
        analysis_depth = depth or self.depth

        try:
            # Evaluate position before move
            eval_before = await self.evaluate_position(board, analysis_depth)

            # Make the move
            board_copy = board.copy()
            board_copy.push(move)

            # Evaluate position after move
            eval_after = await self.evaluate_position(board_copy, analysis_depth)

            # Get top 5 moves for original position
            top_moves = await self.get_top_moves(board, top_n=5, depth=analysis_depth)

            # Get best move info (first in top_moves, or fallback to get_best_move)
            if top_moves:
                best_move_info = top_moves[0]
            else:
                # Fallback if top_moves is empty
                best_move_info = await self.get_best_move(board, analysis_depth)
            
            # Find played move in top moves to get its rank
            played_move_uci = move.uci()
            played_move_rank = None
            for top_move in top_moves:
                if top_move["move"] == played_move_uci:
                    played_move_rank = top_move["rank"]
                    break

            return {
                "eval_before": eval_before["score"],
                "eval_before_str": eval_before["score_str"],
                "eval_after": eval_after["score"],
                "eval_after_str": eval_after["score_str"],
                "best_move": best_move_info["move"],
                "best_move_san": best_move_info["move_san"],
                "eval_best": best_move_info["eval"],
                "eval_best_str": best_move_info["eval_str"],
                "top_moves": top_moves,
                "played_move_eval": eval_after["score"],
                "played_move_eval_str": eval_after["score_str"],
                "played_move_rank": played_move_rank,
            }
        except Exception as e:
            logger.error(f"Error analyzing move: {e}")
            raise

    async def close(self):
        """Close engine connection."""
        if self._engine is not None:
            try:
                await self._engine.quit()
                self._engine = None
                logger.info("Stockfish engine closed")
            except Exception as e:
                logger.error(f"Error closing engine: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global service instance (singleton pattern)
_stockfish_service: Optional[StockfishService] = None


async def get_stockfish_service() -> StockfishService:
    """Get or create Stockfish service instance."""
    global _stockfish_service
    if _stockfish_service is None:
        _stockfish_service = StockfishService()
    return _stockfish_service
