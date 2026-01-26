"""
Game Review Chatbot Agent - Answers questions about reviewed games using cached data.
"""
from typing import Dict, Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.config import settings
from app.models.game import Game, EngineAnalysis, MoveReview, GameSummary
from app.models.base import SessionLocal
from app.services.pgn_service import PGNService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GameReviewChatbotAgent:
    """Chatbot agent for answering questions about reviewed games."""

    def __init__(self):
        """Initialize chatbot agent with Groq LLM."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        self.llm = ChatGroq(
            model=settings.groq_model,
            groq_api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        self.pgn_service = PGNService()

    def _load_game_context(self, game_id: str) -> Dict[str, Any]:
        """
        Load all game context from database.

        Args:
            game_id: Unique game identifier

        Returns:
            Dictionary with game context
        """
        db = SessionLocal()
        try:
            # Load game
            game = db.query(Game).filter(Game.game_id == game_id).first()
            if not game:
                raise ValueError(f"Game {game_id} not found")

            # Load engine analyses
            engine_analyses = (
                db.query(EngineAnalysis)
                .filter(EngineAnalysis.game_id == game_id)
                .order_by(EngineAnalysis.ply)
                .all()
            )

            # Load move reviews
            move_reviews = (
                db.query(MoveReview)
                .filter(MoveReview.game_id == game_id)
                .order_by(MoveReview.ply)
                .all()
            )

            # Load game summary
            summary = (
                db.query(GameSummary)
                .filter(GameSummary.game_id == game_id)
                .first()
            )

            # Format context
            analyses_data = [
                {
                    "ply": a.ply,
                    "move": a.played_move,
                    "best_move": a.best_move,
                    "eval_before": a.eval_before,
                    "eval_after": a.eval_after,
                    "eval_best": a.eval_best,
                }
                for a in engine_analyses
            ]

            reviews_data = [
                {
                    "ply": r.ply,
                    "label": r.label,
                    "explanation": r.explanation,
                }
                for r in move_reviews
            ]

            return {
                "pgn": game.pgn,
                "metadata": game.game_metadata or {},
                "engine_analyses": analyses_data,
                "move_reviews": reviews_data,
                "summary": {
                    "accuracy": summary.accuracy if summary else None,
                    "estimated_rating": summary.estimated_rating if summary else None,
                    "weaknesses": summary.weaknesses if summary else [],
                } if summary else {},
            }
        finally:
            db.close()

    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format game context into prompt-friendly string.

        Args:
            context: Game context dictionary

        Returns:
            Formatted context string
        """
        lines = []

        # Game metadata
        metadata = context.get("metadata", {})
        if metadata:
            lines.append("Game Information:")
            if metadata.get("white"):
                lines.append(f"White: {metadata['white']}")
            if metadata.get("black"):
                lines.append(f"Black: {metadata['black']}")
            if metadata.get("result"):
                lines.append(f"Result: {metadata['result']}")
            lines.append("")

        # Summary
        summary = context.get("summary", {})
        if summary.get("accuracy"):
            lines.append(f"Game Accuracy: {summary['accuracy']}%")
        if summary.get("estimated_rating"):
            lines.append(f"Estimated Rating: {summary['estimated_rating']}")
        if summary.get("weaknesses"):
            lines.append(f"Weaknesses: {', '.join(summary['weaknesses'])}")
        lines.append("")

        # Key moves (mistakes)
        move_reviews = context.get("move_reviews", [])
        mistakes = [r for r in move_reviews if r.get("label") in ["Inaccuracy", "Mistake", "Blunder"]]
        if mistakes:
            lines.append("Key Mistakes:")
            for mistake in mistakes[:10]:  # Limit to 10
                ply = mistake["ply"]
                label = mistake["label"]
                explanation = mistake.get("explanation", "")
                lines.append(f"Move {ply}: {label}")
                if explanation:
                    lines.append(f"  Explanation: {explanation}")
            lines.append("")

        # Sample moves with evaluations
        analyses = context.get("engine_analyses", [])
        if analyses:
            lines.append("Sample Moves (first 5 and last 5):")
            sample_moves = analyses[:5] + analyses[-5:] if len(analyses) > 10 else analyses
            for analysis in sample_moves:
                ply = analysis["ply"]
                move = analysis["move"]
                best = analysis["best_move"]
                eval_after = analysis["eval_after"]
                lines.append(f"Move {ply}: Played {move}, Best {best}, Eval: {eval_after}")
            lines.append("")

        return "\n".join(lines)

    def _create_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Create system prompt with game context and constraints.

        Args:
            context: Game context dictionary

        Returns:
            System prompt string
        """
        context_str = self._format_context_for_prompt(context)

        prompt = f"""You are a chess coach helping a student understand their game. You have access to a complete analysis of their game.

IMPORTANT CONSTRAINTS:
- You CANNOT call Stockfish or any chess engine
- You CANNOT analyze new positions or calculate moves
- You CANNOT speculate about moves not in the game
- You MUST use only the cached analysis data provided below
- Reference specific moves by their move number (ply)
- Use Standard Algebraic Notation (SAN) when possible

GAME CONTEXT:
{context_str}

Answer questions about:
- Why certain moves were better or worse
- What the student should learn from mistakes
- Strategic and tactical concepts in the game
- Patterns and weaknesses identified

Be educational, clear, and reference specific moves and evaluations from the analysis above."""

        return prompt

    async def chat(
        self,
        game_id: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate chatbot response to user message.

        Args:
            game_id: Unique game identifier
            user_message: User's question/message
            conversation_history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]

        Returns:
            Dictionary with response:
            {
                "response": str,
                "game_id": str,
            }
        """
        try:
            # Load game context
            context = self._load_game_context(game_id)

            # Create system prompt
            system_prompt = self._create_system_prompt(context)

            # Build messages
            messages = [SystemMessage(content=system_prompt)]

            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))

            # Add current user message
            messages.append(HumanMessage(content=user_message))

            # Invoke LLM
            response = await self.llm.ainvoke(messages)

            # Extract response text
            response_text = response.content if hasattr(response, "content") else str(response)

            logger.info(f"Generated chatbot response for game {game_id}")

            return {
                "response": response_text,
                "game_id": game_id,
            }
        except Exception as e:
            logger.error(f"Error in chatbot: {e}")
            raise
