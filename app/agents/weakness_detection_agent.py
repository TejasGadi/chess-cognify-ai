"""
Weakness Detection Agent - Identifies recurring mistake patterns using Groq LLM.
"""
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from collections import defaultdict
from app.config import settings
from app.models.game import MoveReview, GameSummary
from app.models.base import SessionLocal
from app.schemas.llm_output import WeaknessOutput
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WeaknessDetectionAgent:
    """Agent for detecting recurring weaknesses in a game."""

    # Labels that indicate mistakes
    MISTAKE_LABELS = ["Inaccuracy", "Mistake", "Blunder"]

    def __init__(self):
        """Initialize weakness detection agent with Groq LLM."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        self.llm = ChatGroq(
            model=settings.groq_model,
            groq_api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        # Create structured output LLM
        self.structured_llm = self.llm.with_structured_output(WeaknessOutput)

        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a chess coach analyzing a student's game to identify recurring weaknesses. 
Your task is to identify high-level patterns and concepts, not specific moves.

Guidelines:
- Focus on chess concepts (e.g., "King safety", "Piece coordination", "Pawn structure")
- Avoid move-specific feedback
- Group similar mistakes together
- Return 3-5 weakness categories maximum
- Use concise, actionable descriptions""",
                ),
                (
                    "human",
                    """Analyze the following mistakes from a chess game and identify recurring weakness patterns:

Game Phase Breakdown:
{phase_breakdown}

Mistakes by Phase:
{mistakes_by_phase}

Return 3-5 weakness categories as a structured list.""",
                ),
            ]
        )

        self.chain = self.prompt_template | self.structured_llm

    def _group_mistakes_by_phase(
        self, classifications: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group mistakes by game phase.

        Args:
            classifications: List of move classifications with phase info

        Returns:
            Dictionary mapping phase -> list of mistakes
        """
        mistakes_by_phase = defaultdict(list)

        for classification in classifications:
            label = classification.get("label", "")
            if label in self.MISTAKE_LABELS:
                phase = classification.get("phase", "unknown")
                mistakes_by_phase[phase].append(classification)

        return dict(mistakes_by_phase)

    def _format_phase_breakdown(
        self, mistakes_by_phase: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Format phase breakdown for prompt.

        Args:
            mistakes_by_phase: Dictionary of mistakes by phase

        Returns:
            Formatted string
        """
        breakdown = []
        for phase, mistakes in mistakes_by_phase.items():
            breakdown.append(f"- {phase.capitalize()}: {len(mistakes)} mistakes")
        return "\n".join(breakdown) if breakdown else "No mistakes found"

    def _format_mistakes_for_prompt(
        self, mistakes_by_phase: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Format mistakes for prompt input.

        Args:
            mistakes_by_phase: Dictionary of mistakes by phase

        Returns:
            Formatted string
        """
        formatted = []
        for phase, mistakes in mistakes_by_phase.items():
            formatted.append(f"\n{phase.capitalize()} mistakes:")
            for mistake in mistakes[:5]:  # Limit to 5 per phase
                ply = mistake.get("ply", 0)
                label = mistake.get("label", "")
                formatted.append(f"  - Move {ply}: {label}")

        return "\n".join(formatted) if formatted else "No mistakes found"


    async def detect_weaknesses(
        self, game_id: str, classifications: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Detect weaknesses in a game.

        Args:
            game_id: Unique game identifier
            classifications: Optional list of classifications (fetches from DB if None)

        Returns:
            List of weakness strings
        """
        # Get classifications if not provided
        if classifications is None:
            db = SessionLocal()
            try:
                reviews = (
                    db.query(MoveReview)
                    .filter(MoveReview.game_id == game_id)
                    .order_by(MoveReview.ply)
                    .all()
                )

                # Get phase info from classifications if available
                # Phase is stored in classification dict, not in MoveReview model
                classifications = [
                    {
                        "ply": r.ply,
                        "label": r.label,
                        "phase": "unknown",  # Will be populated if available
                    }
                    for r in reviews
                ]
            finally:
                db.close()

        if not classifications:
            logger.warning(f"No classifications found for game {game_id}")
            return []

        # Group mistakes by phase
        mistakes_by_phase = self._group_mistakes_by_phase(classifications)

        if not mistakes_by_phase:
            logger.info(f"No mistakes found for game {game_id}")
            return []

        # Format for prompt
        phase_breakdown = self._format_phase_breakdown(mistakes_by_phase)
        mistakes_formatted = self._format_mistakes_for_prompt(mistakes_by_phase)

        try:
            # Invoke LLM with structured output
            result = await self.chain.ainvoke(
                {
                    "phase_breakdown": phase_breakdown,
                    "mistakes_by_phase": mistakes_formatted,
                }
            )

            # Extract weaknesses from structured output
            weaknesses = result.weaknesses

            logger.info(
                f"Detected {len(weaknesses)} weaknesses for game {game_id}"
            )
            return weaknesses
        except Exception as e:
            logger.error(f"Error detecting weaknesses: {e}")
            # Fallback: return generic weakness
            return ["General tactical awareness"]

    async def detect_and_persist_weaknesses(
        self, game_id: str, classifications: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Detect weaknesses and persist to database.

        Args:
            game_id: Unique game identifier
            classifications: Optional list of classifications

        Returns:
            List of weakness strings
        """
        weaknesses = await self.detect_weaknesses(game_id, classifications)

        # Persist to GameSummary
        db = SessionLocal()
        try:
            summary = (
                db.query(GameSummary)
                .filter(GameSummary.game_id == game_id)
                .first()
            )

            if summary:
                summary.weaknesses = weaknesses
            else:
                # Create summary if it doesn't exist
                from app.services.accuracy_rating_service import (
                    AccuracyRatingService,
                )

                accuracy_service = AccuracyRatingService()
                accuracy_metrics = accuracy_service.calculate_game_accuracy(
                    classifications or []
                )
                rating_info = accuracy_service.estimate_rating(
                    accuracy_metrics["accuracy"],
                    accuracy_metrics["blunder_count"],
                )

                summary = GameSummary(
                    game_id=game_id,
                    accuracy=accuracy_metrics["accuracy"],
                    estimated_rating=rating_info["estimated_rating"],
                    rating_confidence=rating_info["confidence"],
                    weaknesses=weaknesses,
                )
                db.add(summary)

            db.commit()
            logger.info(f"Persisted weaknesses for game {game_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error persisting weaknesses: {e}")
            raise
        finally:
            db.close()

        return weaknesses
