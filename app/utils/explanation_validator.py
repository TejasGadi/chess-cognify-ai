"""
Explanation Validator - Wrapper for LLM-based explanation validation.
This module provides a compatibility layer for the LLM-based ExplanationValidatorAgent.
"""
from typing import Dict, Any
from dataclasses import dataclass
from app.utils.logger import get_logger
from app.agents.explanation_validator_agent import ExplanationValidatorAgent
from app.schemas.llm_output import ExplanationValidationOutput
import asyncio

logger = get_logger(__name__)


@dataclass
class ExplanationValidationResult:
    """Result of explanation validation (compatibility wrapper)."""
    is_valid: bool
    discrepancies: list[str]
    confidence_score: float
    needs_revision: bool
    sanitized_explanation: str = ""  # Not used in LLM-based validation, kept for compatibility


class ExplanationValidator:
    """
    Validates AI explanations using LLM-based validation.
    This is a compatibility wrapper around ExplanationValidatorAgent.
    """

    def __init__(self):
        """Initialize validator with LLM-based agent."""
        self.validator_agent = ExplanationValidatorAgent()

    async def validate_explanation_async(
        self,
        explanation: str,
        verified_pieces: Dict[str, Any],
        fen: str,
        played_move_san: str,
        best_move_san: str,
        active_player: str
    ) -> ExplanationValidationResult:
        """
        Validate explanation using LLM (async).
        
        Args:
            explanation: AI-generated explanation text
            verified_pieces: Verified piece positions from position extraction
            fen: FEN string of the current position
            played_move_san: Move that was played (SAN)
            best_move_san: Best move (SAN)
            active_player: Active player (White/Black)
            
        Returns:
            ExplanationValidationResult with validation status and discrepancies
        """
        try:
            result = await self.validator_agent.validate_explanation(
                explanation=explanation,
                verified_pieces=verified_pieces,
                fen=fen,
                played_move_san=played_move_san,
                best_move_san=best_move_san,
                active_player=active_player
            )
            
            # Convert ExplanationValidationOutput to ExplanationValidationResult
            return ExplanationValidationResult(
                is_valid=result.is_valid,
                discrepancies=result.discrepancies,
                confidence_score=result.confidence_score,
                needs_revision=result.needs_revision,
                sanitized_explanation=explanation  # Keep original for compatibility
            )
        except Exception as e:
            logger.error(f"[VALIDATOR] ExplanationValidator - Error in async validation: {e}", exc_info=True)
            return ExplanationValidationResult(
                is_valid=False,
                discrepancies=[f"Validation error: {str(e)}"],
                confidence_score=0.3,
                needs_revision=True,
                sanitized_explanation=explanation
            )
