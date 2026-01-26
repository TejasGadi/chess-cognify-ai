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
        Calculate overall game accuracy.

        Args:
            classifications: List of move classifications with centipawn_loss

        Returns:
            Dictionary with accuracy metrics:
            {
                "accuracy": int,  # Overall game accuracy (0-100)
                "move_accuracies": List[int],  # Per-move accuracies
                "blunder_count": int,
                "mistake_count": int,
                "inaccuracy_count": int,
            }
        """
        if not classifications:
            return {
                "accuracy": 0,
                "move_accuracies": [],
                "blunder_count": 0,
                "mistake_count": 0,
                "inaccuracy_count": 0,
            }

        move_accuracies = []
        blunder_count = 0
        mistake_count = 0
        inaccuracy_count = 0

        for classification in classifications:
            centipawn_loss = classification.get("centipawn_loss", 0)
            accuracy = self.calculate_move_accuracy(centipawn_loss)
            move_accuracies.append(accuracy)

            label = classification.get("label", "").lower()
            if label == "blunder":
                blunder_count += 1
            elif label == "mistake":
                mistake_count += 1
            elif label == "inaccuracy":
                inaccuracy_count += 1

        overall_accuracy = int(mean(move_accuracies)) if move_accuracies else 0

        return {
            "accuracy": overall_accuracy,
            "move_accuracies": move_accuracies,
            "blunder_count": blunder_count,
            "mistake_count": mistake_count,
            "inaccuracy_count": inaccuracy_count,
        }

    def estimate_rating(
        self,
        accuracy: int,
        blunder_count: int,
        time_control: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate player rating based on accuracy and blunder count.

        This is a heuristic estimation, not based on Elo mathematics.

        Args:
            accuracy: Overall game accuracy (0-100)
            blunder_count: Number of blunders in the game
            time_control: Optional time control string (e.g., "600+0")

        Returns:
            Dictionary with rating estimate:
            {
                "estimated_rating": int,
                "confidence": str,  # "low", "medium", "high"
            }
        """
        # Base rating from accuracy
        # Rough mapping: 95+ = 2000+, 85+ = 1600+, 75+ = 1200+, 65+ = 800+
        base_rating = 400 + (accuracy * 16)  # Linear mapping

        # Adjust for blunders
        # Each blunder reduces estimated rating by ~50 points
        blunder_penalty = blunder_count * 50
        estimated_rating = int(base_rating - blunder_penalty)

        # Clamp to reasonable range
        estimated_rating = max(400, min(2500, estimated_rating))

        # Determine confidence
        # Higher confidence if accuracy is consistent and blunders are few
        if blunder_count == 0 and accuracy >= 80:
            confidence = "high"
        elif blunder_count <= 2 and accuracy >= 70:
            confidence = "medium"
        else:
            confidence = "low"

        # Adjust confidence based on time control if provided
        if time_control:
            # Fast time controls (bullet/blitz) may have more blunders
            # but that doesn't necessarily mean lower skill
            try:
                # Parse time control (format: "600+0" or "180+2")
                parts = time_control.split("+")
                initial_seconds = int(parts[0])
                if initial_seconds < 180:  # Bullet
                    confidence = "low" if confidence == "high" else confidence
                elif initial_seconds < 600:  # Blitz
                    if confidence == "high":
                        confidence = "medium"
            except (ValueError, IndexError):
                pass  # Ignore parsing errors

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
        weaknesses: Optional[List[str]] = None,
    ) -> None:
        """
        Persist game summary to database.

        Args:
            game_id: Unique game identifier
            accuracy: Overall game accuracy
            estimated_rating: Estimated player rating
            rating_confidence: Confidence level (low/medium/high)
            weaknesses: Optional list of weaknesses (from Phase 4)
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
                if weaknesses is not None:
                    summary.weaknesses = weaknesses
            else:
                # Create new
                summary = GameSummary(
                    game_id=game_id,
                    accuracy=accuracy,
                    estimated_rating=estimated_rating,
                    rating_confidence=rating_confidence,
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
