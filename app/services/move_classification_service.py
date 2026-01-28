"""
Move classification service - deterministic classification based on evaluation deltas.
"""
from typing import Dict, Any, List, Optional
import re
from app.models.game import EngineAnalysis, MoveReview
from app.models.base import SessionLocal
from app.services.pgn_service import PGNService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MoveClassificationService:
    """Service for classifying moves based on evaluation deltas."""

    # Classification thresholds (in pawns) - chess.com style
    # Best: played move = best move (delta = 0)
    # Good: |delta| <= 0.5 pawns (within 0.5 pawns of best move)
    # Inaccuracy: |delta| <= 1.0 pawns (within 1.0 pawns of best move)
    # Mistake: |delta| <= 2.0 pawns (within 2.0 pawns of best move)
    # Blunder: |delta| > 2.0 pawns (more than 2.0 pawns worse than best move)
    # Note: We use absolute value since delta can be positive (worse for player) or negative (better for player)
    THRESHOLD_GOOD = 0.5
    THRESHOLD_INACCURACY = 1.0
    THRESHOLD_MISTAKE = 2.0

    @staticmethod
    def parse_evaluation(eval_str: str) -> float:
        """
        Parse evaluation string to float (centipawns).

        Args:
            eval_str: Evaluation string (e.g., "+0.4", "-1.2", "M2", "M-3")

        Returns:
            Evaluation in centipawns (float)
        """
        eval_str = eval_str.strip()

        # Check for mate scores
        if eval_str.startswith("M"):
            # Mate in N moves
            try:
                mate_moves = int(eval_str[1:])
                # Convert to large centipawn value
                # Positive = white mates, negative = black mates
                return 10000.0 if mate_moves > 0 else -10000.0
            except ValueError:
                logger.warning(f"Could not parse mate score: {eval_str}")
                return 0.0

        # Parse normal evaluation (in pawns)
        try:
            pawns = float(eval_str)
            # Convert to centipawns
            return pawns * 100.0
        except ValueError:
            logger.warning(f"Could not parse evaluation: {eval_str}")
            return 0.0

    @staticmethod
    def calculate_evaluation_delta(
        eval_after: str, eval_best: str
    ) -> float:
        """
        Calculate evaluation delta (eval_after - eval_best).

        Args:
            eval_after: Evaluation after played move (string)
            eval_best: Evaluation of best move (string)

        Returns:
            Delta in centipawns (negative = worse than best)
        """
        eval_after_cp = MoveClassificationService.parse_evaluation(eval_after)
        eval_best_cp = MoveClassificationService.parse_evaluation(eval_best)

        return eval_after_cp - eval_best_cp

    @staticmethod
    def classify_move(
        played_move: str, best_move: str, eval_after: str, eval_best: str
    ) -> Dict[str, Any]:
        """
        Classify a move based on evaluation delta.

        Args:
            played_move: Move played (UCI format)
            best_move: Best move (UCI format)
            eval_after: Evaluation after played move
            eval_best: Evaluation of best move

        Returns:
            Dictionary with classification:
            {
                "label": str,  # Best, Good, Inaccuracy, Mistake, Blunder
                "centipawn_loss": int,
                "delta": float,  # In centipawns
            }
        """
        # Check if played move is best move
        if played_move.lower() == best_move.lower():
            return {
                "label": "Best",
                "centipawn_loss": 0,
                "delta": 0.0,
            }

        # Calculate delta
        delta_cp = MoveClassificationService.calculate_evaluation_delta(
            eval_after, eval_best
        )

        # Convert to pawns for threshold comparison
        # Use absolute value since delta can be positive (worse for player) or negative (better for player)
        delta_pawns = abs(delta_cp) / 100.0

        # Classify based on thresholds
        if delta_pawns <= MoveClassificationService.THRESHOLD_GOOD:
            label = "Good"
        elif delta_pawns <= MoveClassificationService.THRESHOLD_INACCURACY:
            label = "Inaccuracy"
        elif delta_pawns <= MoveClassificationService.THRESHOLD_MISTAKE:
            label = "Mistake"
        else:
            label = "Blunder"

        # Centipawn loss is the absolute value of delta (always positive)
        centipawn_loss = int(abs(delta_cp))

        return {
            "label": label,
            "centipawn_loss": centipawn_loss,
            "delta": delta_cp,
        }

    def classify_game_moves(
        self, game_id: str, analyses: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Classify all moves in a game.

        Args:
            game_id: Unique game identifier
            analyses: Optional list of engine analyses (fetches from DB if None)

        Returns:
            List of classification dictionaries
        """
        # Fetch analyses from database if not provided
        if analyses is None:
            db = SessionLocal()
            try:
                db_analyses = (
                    db.query(EngineAnalysis)
                    .filter(EngineAnalysis.game_id == game_id)
                    .order_by(EngineAnalysis.ply)
                    .all()
                )
                analyses = [
                    {
                        "ply": a.ply,
                        "played_move": a.played_move,
                        "best_move": a.best_move,
                        "eval_after": a.eval_after,
                        "eval_best": a.eval_best,
                    }
                    for a in db_analyses
                ]
            finally:
                db.close()

        if not analyses:
            logger.warning(f"No analyses found for game {game_id}")
            return []

        classifications = []
        for analysis in analyses:
            classification = self.classify_move(
                analysis["played_move"],
                analysis["best_move"],
                analysis["eval_after"],
                analysis["eval_best"],
            )
            classification["ply"] = analysis["ply"]
            classifications.append(classification)

        return classifications

    def persist_classifications(
        self, game_id: str, classifications: List[Dict[str, Any]]
    ) -> None:
        """
        Persist move classifications to database.

        Args:
            game_id: Unique game identifier
            classifications: List of classification dictionaries
        """
        db = SessionLocal()
        try:
            for classification in classifications:
                ply = classification["ply"]

                # Check if already exists
                existing = (
                    db.query(MoveReview)
                    .filter(
                        MoveReview.game_id == game_id,
                        MoveReview.ply == ply,
                    )
                    .first()
                )

                if existing:
                    # Update existing record
                    existing.label = classification["label"]
                    existing.centipawn_loss = classification["centipawn_loss"]
                else:
                    # Create new record
                    move_review = MoveReview(
                        game_id=game_id,
                        ply=ply,
                        label=classification["label"],
                        centipawn_loss=classification["centipawn_loss"],
                    )
                    db.add(move_review)

            db.commit()
            logger.info(
                f"Persisted {len(classifications)} move classifications for game {game_id}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error persisting classifications: {e}")
            raise
        finally:
            db.close()

    def add_game_phases(
        self,
        game_id: str,
        classifications: List[Dict[str, Any]],
        pgn_string: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Add game phase information to classifications.

        Args:
            game_id: Unique game identifier
            classifications: List of classification dictionaries
            pgn_string: Optional PGN string (fetches from DB if None)

        Returns:
            Classifications with added phase information
        """
        # Get PGN if not provided
        if pgn_string is None:
            db = SessionLocal()
            try:
                from app.models.game import Game

                game = db.query(Game).filter(Game.game_id == game_id).first()
                if game:
                    pgn_string = game.pgn
                else:
                    logger.warning(f"Game {game_id} not found, skipping phase detection")
                    return classifications
            finally:
                db.close()

        if not pgn_string:
            return classifications

        # Parse PGN and get game object
        game = self.pgn_service.parse_pgn(pgn_string)
        if not game:
            return classifications

        # Get total plies
        total_plies = self.pgn_service.get_total_plies(game)

        # Add phase to each classification
        for classification in classifications:
            ply = classification["ply"]
            board = self.pgn_service.get_position_after_move(game, ply)
            if board:
                phase = self.pgn_service.detect_game_phase(ply, total_plies, board)
                classification["phase"] = phase
            else:
                classification["phase"] = "unknown"

        return classifications

    def __init__(self):
        """Initialize move classification service."""
        self.pgn_service = PGNService()
