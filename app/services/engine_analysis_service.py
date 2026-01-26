"""
Engine analysis service - orchestrates Stockfish analysis for games.
"""
from typing import List, Dict, Any, Optional
import chess
import chess.pgn
from app.services.stockfish_service import get_stockfish_service, StockfishService
from app.services.pgn_service import PGNService
from app.utils.cache import get_cache_key, get_from_cache, set_to_cache
from app.utils.logger import get_logger
from app.models.game import EngineAnalysis
from app.models.base import SessionLocal

logger = get_logger(__name__)


class EngineAnalysisService:
    """Service for analyzing chess games with Stockfish."""

    def __init__(self):
        """Initialize engine analysis service."""
        self.pgn_service = PGNService()

    async def analyze_move(
        self,
        game: chess.pgn.Game,
        ply: int,
        game_id: str,
        stockfish: Optional[StockfishService] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze a single move in a game.

        Args:
            game: chess.pgn.Game object
            ply: Half-move number (1-indexed)
            game_id: Unique game identifier
            stockfish: Stockfish service instance (creates new if None)
            use_cache: Whether to use cached results

        Returns:
            Dictionary with analysis results matching EngineAnalysis schema
        """
        # Check cache first
        if use_cache:
            cache_key = get_cache_key(game_id, ply)
            cached = get_from_cache(cache_key)
            if cached:
                logger.debug(f"Using cached analysis for game {game_id}, ply {ply}")
                return cached

        # Get Stockfish service
        if stockfish is None:
            stockfish = await get_stockfish_service()

        try:
            # Get position before move
            board_before = self.pgn_service.get_position_before_move(game, ply)
            if board_before is None:
                raise ValueError(f"Invalid ply: {ply}")

            # Get the move played
            move = self.pgn_service.get_move_at_ply(game, ply)
            if move is None:
                raise ValueError(f"No move found at ply {ply}")

            # Analyze the move
            analysis = await stockfish.analyze_move(board_before, move)

            # Get FEN before move
            fen_before = board_before.fen()

            # Format results
            result = {
                "ply": ply,
                "fen": fen_before,
                "played_move": move.uci(),
                "best_move": analysis["best_move"],
                "eval_before": str(analysis["eval_before_str"]),
                "eval_after": str(analysis["eval_after_str"]),
                "eval_best": str(analysis["eval_best_str"]),
                "top_moves": analysis.get("top_moves", []),
                "played_move_eval": str(analysis.get("played_move_eval_str", analysis["eval_after_str"])),
                "played_move_rank": analysis.get("played_move_rank"),
            }

            # Cache the result
            if use_cache:
                cache_key = get_cache_key(game_id, ply)
                set_to_cache(cache_key, result)

            return result
        except Exception as e:
            logger.error(f"Error analyzing move at ply {ply}: {e}")
            raise

    async def analyze_game(
        self,
        pgn_string: str,
        game_id: str,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Analyze all moves in a game.

        Args:
            pgn_string: PGN format string
            game_id: Unique game identifier
            use_cache: Whether to use cached results

        Returns:
            List of analysis results, one per move
        """
        # Parse PGN
        game = self.pgn_service.parse_pgn(pgn_string)
        if game is None:
            raise ValueError("Failed to parse PGN")

        # Get total plies
        total_plies = self.pgn_service.get_total_plies(game)

        # Get Stockfish service (reuse for all moves)
        stockfish = await get_stockfish_service()

        results = []
        for ply in range(1, total_plies + 1):
            try:
                analysis = await self.analyze_move(
                    game, ply, game_id, stockfish, use_cache
                )
                results.append(analysis)
                logger.info(f"Analyzed move {ply}/{total_plies} for game {game_id}")
            except Exception as e:
                logger.error(f"Failed to analyze ply {ply}: {e}")
                # Continue with next move instead of failing entire game
                continue

        return results

    async def persist_analysis(
        self, game_id: str, analyses: List[Dict[str, Any]]
    ) -> None:
        """
        Persist analysis results to database.

        Args:
            game_id: Unique game identifier
            analyses: List of analysis dictionaries
        """
        db = SessionLocal()
        try:
            for analysis in analyses:
                # Check if already exists
                existing = (
                    db.query(EngineAnalysis)
                    .filter(
                        EngineAnalysis.game_id == game_id,
                        EngineAnalysis.ply == analysis["ply"],
                    )
                    .first()
                )

                if existing:
                    # Update existing record
                    existing.fen = analysis["fen"]
                    existing.played_move = analysis["played_move"]
                    existing.best_move = analysis["best_move"]
                    existing.eval_before = analysis["eval_before"]
                    existing.eval_after = analysis["eval_after"]
                    existing.eval_best = analysis["eval_best"]
                    # Update top moves data if available
                    if "top_moves" in analysis:
                        existing.top_moves = analysis["top_moves"]
                    if "played_move_eval" in analysis:
                        existing.played_move_eval = analysis["played_move_eval"]
                    if "played_move_rank" in analysis:
                        existing.played_move_rank = analysis["played_move_rank"]
                else:
                    # Create new record
                    db_analysis = EngineAnalysis(
                        game_id=game_id,
                        ply=analysis["ply"],
                        fen=analysis["fen"],
                        played_move=analysis["played_move"],
                        best_move=analysis["best_move"],
                        eval_before=analysis["eval_before"],
                        eval_after=analysis["eval_after"],
                        eval_best=analysis["eval_best"],
                        top_moves=analysis.get("top_moves"),
                        played_move_eval=analysis.get("played_move_eval"),
                        played_move_rank=analysis.get("played_move_rank"),
                    )
                    db.add(db_analysis)

            db.commit()
            logger.info(f"Persisted {len(analyses)} analysis results for game {game_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error persisting analysis: {e}")
            raise
        finally:
            db.close()

    async def get_cached_analysis(
        self, game_id: str, plies: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get cached analysis results from database.

        Args:
            game_id: Unique game identifier
            plies: Optional list of specific plies to retrieve

        Returns:
            List of analysis dictionaries
        """
        db = SessionLocal()
        try:
            query = db.query(EngineAnalysis).filter(
                EngineAnalysis.game_id == game_id
            )

            if plies:
                query = query.filter(EngineAnalysis.ply.in_(plies))

            results = query.order_by(EngineAnalysis.ply).all()

            return [
                {
                    "ply": r.ply,
                    "fen": r.fen,
                    "played_move": r.played_move,
                    "best_move": r.best_move,
                    "eval_before": r.eval_before,
                    "eval_after": r.eval_after,
                    "eval_best": r.eval_best,
                }
                for r in results
            ]
        finally:
            db.close()
