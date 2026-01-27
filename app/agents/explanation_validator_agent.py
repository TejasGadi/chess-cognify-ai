"""
Explanation Validator Agent - Validates AI explanations using LLM.
Checks for hallucinations, impossible moves, and incorrect piece positions.
"""
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.llm_output import ExplanationValidationOutput
from app.utils.logger import get_logger
from app.utils.llm_factory import get_llm
import chess

logger = get_logger(__name__)


class ExplanationValidatorAgent:
    """Agent for validating AI explanations using LLM."""

    def __init__(self):
        """Initialize explanation validator agent with OpenAI LLM."""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        logger.info(f"[AGENT] ExplanationValidatorAgent - Using OpenAI model: {settings.openai_model}")
        
        self.llm = get_llm(use_vision=False, require_primary=True)
        
        # Create structured output LLM
        self.structured_llm = self.llm.with_structured_output(ExplanationValidationOutput)
        
        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a chess explanation validator. Your task is to validate AI-generated chess move explanations for accuracy and correctness.

**CRITICAL REQUIREMENTS:**
1. Check if the explanation mentions pieces on squares that actually exist in the verified positions
2. Check if the explanation mentions moves that are legally possible from the current position
3. Check if the explanation mentions impossible moves (e.g., "knight from b3 to c4" when that move is illegal)
4. Identify any hallucinations or factual errors
5. Be thorough and specific in identifying errors

**VALIDATION CRITERIA:**
- ✅ VALID: Explanation only mentions pieces that exist on the squares stated in verified positions
- ✅ VALID: Explanation only mentions moves that are legally possible from the current position
- ❌ INVALID: Explanation mentions a piece on a square where no such piece exists
- ❌ INVALID: Explanation mentions an impossible move (e.g., illegal knight move, piece can't reach that square)
- ❌ INVALID: Explanation mentions a piece moving from a square where it doesn't exist
- ❌ INVALID: Explanation contradicts the verified piece positions

**OUTPUT FORMAT:**
- is_valid: true if explanation is completely correct, false if any errors found
- discrepancies: List of specific errors found (be detailed and specific)
- confidence_score: Your confidence in the validation (0.0 to 1.0)
- needs_revision: true if explanation has errors that need correction

**EXAMPLES OF ERRORS TO CATCH:**
1. "Knight on b5 attacks..." when verified positions show knight is on b3
2. "Knight from b3 to c4" when that move is illegal (knight can't move from b3 to c4)
3. "Queen on d5" when verified positions show queen is on d1
4. "Bishop can move to e4" when bishop is blocked or that square is unreachable
5. Any mention of pieces on squares not in the verified positions list

**IMPORTANT:**
- Use the verified piece positions as the ground truth
- Use the FEN position to check move legality
- Be specific about what is wrong (e.g., "Mentions knight on b5 but knight is actually on b3")
- If a move is mentioned, verify it's legal from the current position""",
                ),
                (
                    "human",
                    """Validate this chess move explanation:

**EXPLANATION TO VALIDATE:**
{explanation}

**VERIFIED PIECE POSITIONS (GROUND TRUTH):**
{verified_pieces}

**CURRENT POSITION (FEN):**
{fen}

**MOVE CONTEXT:**
- Move played: {played_move_san}
- Best move: {best_move_san}
- Active player: {active_player}

**INSTRUCTIONS:**
1. Carefully read the explanation
2. Check every piece-square mention against the verified positions
3. Check if any moves mentioned are legally possible from the FEN position
4. Identify ALL errors (piece positions, impossible moves, contradictions)
5. List specific discrepancies with details
6. Set confidence_score based on how many errors you find (fewer errors = higher confidence)
7. Set needs_revision=true if ANY errors are found

**CRITICAL:** Be thorough. Even one error means the explanation needs revision.""",
                ),
            ]
        )
        
        # Create chain
        self.chain = self.prompt_template | self.structured_llm
        
        logger.info("[AGENT] ExplanationValidatorAgent initialized successfully")

    async def validate_explanation(
        self,
        explanation: str,
        verified_pieces: Dict[str, Any],
        fen: str,
        played_move_san: str,
        best_move_san: str,
        active_player: str
    ) -> ExplanationValidationOutput:
        """
        Validate explanation using LLM.
        
        Args:
            explanation: AI-generated explanation text
            verified_pieces: Verified piece positions from position extraction
            fen: FEN string of the current position
            played_move_san: Move that was played (SAN)
            best_move_san: Best move (SAN)
            active_player: Active player (White/Black)
            
        Returns:
            ExplanationValidationOutput with validation results
        """
        try:
            logger.debug(f"[AGENT] ExplanationValidatorAgent - Validating explanation (length: {len(explanation)} chars)")
            
            # Format verified pieces for prompt
            verified_pieces_text = self._format_verified_pieces(verified_pieces)
            
            # Get Langfuse callback handler for tracing
            from app.utils.langfuse_handler import get_langfuse_handler
            langfuse_handler = get_langfuse_handler()
            
            config = {}
            if langfuse_handler:
                config["callbacks"] = [langfuse_handler]
            
            logger.debug(f"[AGENT] ExplanationValidatorAgent - Invoking LLM for explanation validation")
            result = await self.chain.ainvoke(
                {
                    "explanation": explanation,
                    "verified_pieces": verified_pieces_text,
                    "fen": fen,
                    "played_move_san": played_move_san,
                    "best_move_san": best_move_san,
                    "active_player": active_player,
                },
                config=config
            )
            
            logger.info(
                f"[AGENT] ExplanationValidatorAgent - Validation complete: "
                f"valid={result.is_valid}, discrepancies={len(result.discrepancies)}, "
                f"confidence={result.confidence_score:.2f}, needs_revision={result.needs_revision}"
            )
            
            if result.discrepancies:
                for i, disc in enumerate(result.discrepancies[:5], 1):
                    logger.warning(f"[AGENT] ExplanationValidatorAgent - Discrepancy {i}: {disc}")
            
            return result
            
        except Exception as e:
            logger.error(f"[AGENT] ExplanationValidatorAgent - Error validating explanation: {e}", exc_info=True)
            # On error, return invalid result with low confidence
            return ExplanationValidationOutput(
                is_valid=False,
                discrepancies=[f"Validation error: {str(e)}"],
                confidence_score=0.3,
                needs_revision=True
            )

    def _format_verified_pieces(self, verified_pieces: Dict[str, Any]) -> str:
        """Format verified pieces for prompt."""
        lines = []
        lines.append("White pieces:")
        white_pieces = verified_pieces.get("white", {})
        for piece_type in ['King', 'Queen', 'Rooks', 'Bishops', 'Knights', 'Pawns']:
            squares = white_pieces.get(piece_type, [])
            if squares:
                lines.append(f"  {piece_type}: {', '.join(squares)}")
        
        lines.append("")
        lines.append("Black pieces:")
        black_pieces = verified_pieces.get("black", {})
        for piece_type in ['King', 'Queen', 'Rooks', 'Bishops', 'Knights', 'Pawns']:
            squares = black_pieces.get(piece_type, [])
            if squares:
                lines.append(f"  {piece_type}: {', '.join(squares)}")
        
        lines.append("")
        lines.append(f"Active color: {verified_pieces.get('active_color', 'Unknown')}")
        
        return "\n".join(lines)
