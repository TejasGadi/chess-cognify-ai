"""
Accuracy and rating estimation service.
"""
from typing import Dict, Any, List, Optional
from statistics import mean
from app.models.game import MoveReview, GameSummary
from app.models.base import SessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AccuracyRatingService:
    """Service for calculating accuracy and estimating ratings."""

    # Accuracy calculation constant (K in formula: max(0, 100 - (centipawn_loss * K)))
    ACCURACY_K = 1.0  # Tunable parameter (0.8-1.2 range)

    def calculate_move_accuracy(self, centipawn_loss: int) -> int:
        """
        Calculate accuracy for a single move.

        Formula: max(0, 100 - (centipawn_loss * K))

        Args:
            centipawn_loss: Centipawn loss for the move

        Returns:
            Accuracy score (0-100)
        """
        accuracy = 100 - (centipawn_loss * self.ACCURACY_K)
        return max(0, int(accuracy))

    def calculate_game_accuracy(
        self, classifications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate detailed game accuracy metrics, including per-player and per-phase stats.

        Args:
            classifications: List of move classifications with centipawn_loss, ply, and phase

        Returns:
            Dictionary with comprehensive accuracy metrics:
            {
                "accuracy": int,  # Overall
                "white_accuracy": int,
                "black_accuracy": int,
                "move_counts": {
                    "white": { "Best": X, "Good": Y, ... },
                    "black": { "Best": A, "Good": B, ... }
                },
                "phase_stats": {
                    "white": { "opening": {"accuracy": X, "moves": N}, ... },
                    "black": { "opening": {"accuracy": A, "moves": M}, ... }
                }
            }
        """
        if not classifications:
            return {
                "accuracy": 0,
                "white_accuracy": 0,
                "black_accuracy": 0,
                "move_counts": {"white": {}, "black": {}},
                "phase_stats": {"white": {}, "black": {}},
            }

        labels = ["Best", "Good", "Inaccuracy", "Mistake", "Blunder"]
        
        # Initialize stats
        results = {
            "white": {"moves": [], "counts": {l: 0 for l in labels}, "phases": {}},
            "black": {"moves": [], "counts": {l: 0 for l in labels}, "phases": {}}
        }

        for classification in classifications:
            ply = classification.get("ply", 0)
            is_white = (ply % 2 != 0)  # Ply 1, 3, 5... are White
            player_key = "white" if is_white else "black"
            
            centipawn_loss = classification.get("centipawn_loss", 0)
            accuracy = self.calculate_move_accuracy(centipawn_loss)
            
            label = classification.get("label", "Good")
            phase = classification.get("phase", "middlegame")

            # Update player stats
            results[player_key]["moves"].append(accuracy)
            if label in results[player_key]["counts"]:
                results[player_key]["counts"][label] += 1
            
            # Update phase stats
            if phase not in results[player_key]["phases"]:
                results[player_key]["phases"][phase] = []
            results[player_key]["phases"][phase].append(accuracy)

        # Calculate averages
        white_acc = int(mean(results["white"]["moves"])) if results["white"]["moves"] else 0
        black_acc = int(mean(results["black"]["moves"])) if results["black"]["moves"] else 0
        overall_acc = int(mean(results["white"]["moves"] + results["black"]["moves"])) if (results["white"]["moves"] or results["black"]["moves"]) else 0

        # Format phase statistics
        phase_stats = {"white": {}, "black": {}}
        for color in ["white", "black"]:
            for phase, accs in results[color]["phases"].items():
                phase_stats[color][phase] = {
                    "accuracy": int(mean(accs)) if accs else 0,
                    "count": len(accs)
                }

        return {
            "accuracy": overall_acc,
            "white_accuracy": white_acc,
            "black_accuracy": black_acc,
            "move_counts": {
                "white": results["white"]["counts"],
                "black": results["black"]["counts"]
            },
            "phase_stats": phase_stats,
            "blunder_count": results["white"]["counts"].get("Blunder", 0) + results["black"]["counts"].get("Blunder", 0) # For legacy reasons
        }

    def estimate_rating(
        self,
        accuracy: int,
        count_stats: Dict[str, int],
        time_control: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate player rating based on accuracy and move counts.
        """
        # Base rating from accuracy
        base_rating = 400 + (accuracy * 20)  # Slightly more aggressive linear mapping
        
        # Penalties for negative classifications
        blunder_penalty = count_stats.get("Blunder", 0) * 60
        mistake_penalty = count_stats.get("Mistake", 0) * 30
        inaccuracy_penalty = count_stats.get("Inaccuracy", 0) * 10
        
        estimated_rating = int(base_rating - blunder_penalty - mistake_penalty - inaccuracy_penalty)

        # Clamp to reasonable range
        estimated_rating = max(400, min(2800, estimated_rating))

        # Determine confidence
        blunder_count = count_stats.get("Blunder", 0)
        if blunder_count == 0 and accuracy >= 85:
            confidence = "high"
        elif blunder_count <= 2 and accuracy >= 70:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "estimated_rating": estimated_rating,
            "confidence": confidence,
        }

    def update_move_accuracies(
        self, game_id: str, classifications: List[Dict[str, Any]]
    ) -> None:
        """
        Update move review records with accuracy scores.

        Args:
            game_id: Unique game identifier
            classifications: List of classifications with centipawn_loss
        """
        db = SessionLocal()
        try:
            for classification in classifications:
                ply = classification["ply"]
                centipawn_loss = classification.get("centipawn_loss", 0)
                accuracy = self.calculate_move_accuracy(centipawn_loss)

                # Update MoveReview record
                move_review = (
                    db.query(MoveReview)
                    .filter(
                        MoveReview.game_id == game_id,
                        MoveReview.ply == ply,
                    )
                    .first()
                )

                if move_review:
                    move_review.accuracy = accuracy
                else:
                    logger.warning(
                        f"MoveReview not found for game {game_id}, ply {ply}"
                    )

            db.commit()
            logger.info(f"Updated move accuracies for game {game_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating move accuracies: {e}")
            raise
        finally:
            db.close()

    def persist_game_summary(
        self,
        game_id: str,
        accuracy: int,
        estimated_rating: int,
        rating_confidence: str,
        details: Optional[Dict[str, Any]] = None,
        weaknesses: Optional[List[str]] = None,
    ) -> None:
        """
        Persist game summary to database.

        Args:
            game_id: Unique game identifier
            accuracy: Overall game accuracy
            estimated_rating: Estimated player rating
            rating_confidence: Confidence level (low/medium/high)
            details: Detailed stats (per player accuracy, counts, etc.)
            weaknesses: Optional list of weaknesses
        """
        db = SessionLocal()
        try:
            # Check if summary exists
            summary = (
                db.query(GameSummary)
                .filter(GameSummary.game_id == game_id)
                .first()
            )

            if summary:
                # Update existing
                summary.accuracy = accuracy
                summary.estimated_rating = estimated_rating
                summary.rating_confidence = rating_confidence
                if details is not None:
                    summary.details = details
                if weaknesses is not None:
                    summary.weaknesses = weaknesses
            else:
                # Create new
                summary = GameSummary(
                    game_id=game_id,
                    accuracy=accuracy,
                    estimated_rating=estimated_rating,
                    rating_confidence=rating_confidence,
                    details=details or {},
                    weaknesses=weaknesses or [],
                )
                db.add(summary)

            db.commit()
            logger.info(f"Persisted game summary for game {game_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error persisting game summary: {e}")
            raise
        finally:
            db.close()

    def get_classifications_for_game(
        self, game_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get move classifications for a game from database.

        Args:
            game_id: Unique game identifier

        Returns:
            List of classification dictionaries
        """
        db = SessionLocal()
        try:
            reviews = (
                db.query(MoveReview)
                .filter(MoveReview.game_id == game_id)
                .order_by(MoveReview.ply)
                .all()
            )

            return [
                {
                    "ply": r.ply,
                    "label": r.label,
                    "centipawn_loss": r.centipawn_loss or 0,
                    "accuracy": r.accuracy,
                }
                for r in reviews
            ]
        finally:
            db.close()
