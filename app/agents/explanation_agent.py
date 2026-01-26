"""
Explanation Agent - Generates human-readable explanations for chess mistakes using Groq LLM.
"""
from typing import Dict, Any, Optional, List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.models.game import MoveReview, EngineAnalysis
from app.models.base import SessionLocal
from app.schemas.llm_output import ExplanationOutput
from app.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)


class ExplanationAgent:
    """Agent for generating move explanations using Groq LLM."""

    # Generate explanations for ALL moves (not just mistakes)
    EXPLANATION_LABELS = ["Best", "Good", "Inaccuracy", "Mistake", "Blunder"]

    def __init__(self):
        """Initialize explanation agent with Groq LLM."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        self.llm = ChatGroq(
            model=settings.groq_model,
            groq_api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        # Create structured output LLM
        self.structured_llm = self.llm.with_structured_output(ExplanationOutput)

        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a chess coach providing move analysis. Your comments should be:
- Clear and educational, focusing on chess concepts (piece activity, king safety, tactics, strategy)
- Avoid engine jargon (no centipawns, no depth, no variations)
- Maximum 4 sentences
- Use Standard Algebraic Notation (SAN) for moves
- Format your response as a natural comment on the user's move

Comment format:
- If it's the best move: "This is the best move because [reason]"
- If it's a slight mistake: "This is a slight mistake because [reason]. Best move is "[best_move]". But your move is not bad/losing, [context]"
- If it's a mistake/blunder: "This is a [mistake/blunder] because [reason]. Best move is "[best_move]". You missed [tactic/opportunity/threat]"
- Always mention the best move explicitly""",
                ),
                (
                    "human",
                    """Analyze this chess move:

Position (FEN): {fen}
Move played: {played_move_san} (Evaluation: {played_move_eval})
Best move: {best_move_san} (Evaluation: {best_move_eval})
Move quality: {label}
{top_moves_context}

Provide a comment on the user's move following the format:
- If best move: "This is the best move because..."
- If slight mistake: "This is a slight mistake because... Best move is "[best_move_san]". But your move is not bad/losing..."
- If mistake/blunder: "This is a [label] because... Best move is "[best_move_san]". You missed [tactic/opportunity]..."

Always be educational and mention specific chess concepts.""",
                ),
            ]
        )

        self.chain = self.prompt_template | self.structured_llm

    def _convert_uci_to_san(self, uci_move: str, fen: str) -> str:
        """
        Convert UCI move to SAN notation.

        Args:
            uci_move: Move in UCI format (e.g., "e2e4")
            fen: Position FEN string

        Returns:
            Move in SAN format (e.g., "e4")
        """
        try:
            import chess
            board = chess.Board(fen)
            move = chess.Move.from_uci(uci_move)
            return board.san(move)
        except Exception as e:
            logger.warning(f"Error converting UCI to SAN: {e}, using UCI")
            return uci_move

    async def generate_explanation(
        self,
        fen: str,
        played_move: str,
        best_move: str,
        label: str,
        eval_change: str,
        top_moves: Optional[List[Dict[str, Any]]] = None,
        played_move_eval: Optional[str] = None,
        best_move_eval: Optional[str] = None,
    ) -> str:
        """
        Generate explanation for a move.

        Args:
            fen: Position FEN before move
            played_move: Move played (UCI format)
            best_move: Best move (UCI format)
            label: Move classification (Inaccuracy/Mistake/Blunder)
            eval_change: Evaluation change description
            top_moves: List of top 5 moves with evaluations
            played_move_eval: Evaluation of played move
            best_move_eval: Evaluation of best move

        Returns:
            Explanation text (max 4 sentences)
        """
        try:
            # Convert UCI to SAN
            played_move_san = self._convert_uci_to_san(played_move, fen)
            best_move_san = self._convert_uci_to_san(best_move, fen)

            # Build top moves context
            top_moves_context = ""
            if top_moves:
                top_moves_context = "Top engine moves in this position:\n"
                for i, move_info in enumerate(top_moves[:5], 1):
                    move_san = move_info.get("move_san", move_info.get("move", "N/A"))
                    eval_str = move_info.get("eval_str", "N/A")
                    top_moves_context += f"{i}. {move_san} (Evaluation: {eval_str})\n"
            else:
                top_moves_context = "Top engine moves: Not available"

            # Invoke chain with structured output
            result = await self.chain.ainvoke(
                {
                    "fen": fen,
                    "played_move_san": played_move_san,
                    "best_move_san": best_move_san,
                    "label": label,
                    "eval_change": eval_change,
                    "top_moves_context": top_moves_context,
                    "played_move_eval": played_move_eval or eval_change.split("->")[-1].strip() if "->" in eval_change else "N/A",
                    "best_move_eval": best_move_eval or eval_change.split("->")[0].strip() if "->" in eval_change else "N/A",
                }
            )

            # Extract explanation from structured output
            explanation = result.explanation.strip()
            if len(explanation) > 500:  # Safety check
                explanation = explanation[:500] + "..."

            return explanation
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            # Fallback explanation
            return f"This {label.lower()} weakens your position. The best move {best_move} would have been stronger."

    async def explain_move(
        self, game_id: str, ply: int, use_cache: bool = True
    ) -> Optional[str]:
        """
        Generate explanation for a specific move in a game.

        Args:
            game_id: Unique game identifier
            ply: Half-move number
            use_cache: Whether to use cached explanation

        Returns:
            Explanation text or None if move doesn't need explanation
        """
        db = SessionLocal()
        try:
            # Get move review
            move_review = (
                db.query(MoveReview)
                .filter(
                    MoveReview.game_id == game_id,
                    MoveReview.ply == ply,
                )
                .first()
            )

            if not move_review:
                logger.warning(f"MoveReview not found for game {game_id}, ply {ply}")
                return None

            # Check if explanation already exists
            if use_cache and move_review.explanation:
                return move_review.explanation

            # Generate explanation for all moves
            # (EXPLANATION_LABELS now includes all labels)

            # Get engine analysis for context
            engine_analysis = (
                db.query(EngineAnalysis)
                .filter(
                    EngineAnalysis.game_id == game_id,
                    EngineAnalysis.ply == ply,
                )
                .first()
            )

            if not engine_analysis:
                logger.warning(
                    f"EngineAnalysis not found for game {game_id}, ply {ply}"
                )
                return None

            # Generate explanation with top moves data
            eval_change = f"{engine_analysis.eval_before} -> {engine_analysis.eval_after}"
            top_moves = engine_analysis.top_moves if hasattr(engine_analysis, 'top_moves') and engine_analysis.top_moves else None
            played_move_eval = engine_analysis.played_move_eval if hasattr(engine_analysis, 'played_move_eval') else None
            best_move_eval = engine_analysis.eval_best
            
            explanation = await self.generate_explanation(
                fen=engine_analysis.fen,
                played_move=engine_analysis.played_move,
                best_move=engine_analysis.best_move,
                label=move_review.label,
                eval_change=eval_change,
                top_moves=top_moves,
                played_move_eval=played_move_eval,
                best_move_eval=best_move_eval,
            )

            # Update move review with explanation
            move_review.explanation = explanation
            db.commit()

            logger.info(f"Generated explanation for game {game_id}, ply {ply}")
            return explanation
        except Exception as e:
            db.rollback()
            logger.error(f"Error explaining move: {e}")
            raise
        finally:
            db.close()

    async def explain_game_moves(
        self, game_id: str, use_cache: bool = True
    ) -> Dict[int, str]:
        """
        Generate explanations for all moves in a game.

        Args:
            game_id: Unique game identifier
            use_cache: Whether to use cached explanations

        Returns:
            Dictionary mapping ply -> explanation
        """
        db = SessionLocal()
        try:
            # Get all moves (generate explanations for all moves)
            move_reviews = (
                db.query(MoveReview)
                .filter(MoveReview.game_id == game_id)
                .order_by(MoveReview.ply)
                .all()
            )

            explanations = {}
            for move_review in move_reviews:
                # Check cache
                if use_cache and move_review.explanation:
                    explanations[move_review.ply] = move_review.explanation
                    continue

                # Generate explanation
                try:
                    explanation = await self.explain_move(
                        game_id, move_review.ply, use_cache=False
                    )
                    if explanation:
                        explanations[move_review.ply] = explanation
                except Exception as e:
                    logger.error(
                        f"Error explaining ply {move_review.ply}: {e}, skipping"
                    )
                    # Continue with next move
                    continue

            logger.info(
                f"Generated {len(explanations)} explanations for game {game_id}"
            )
            return explanations
        finally:
            db.close()
