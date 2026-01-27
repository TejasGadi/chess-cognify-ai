"""
Position Extraction Agent - Extracts piece positions from chess positions using LLM.
This is the first step in multi-step reasoning to prevent position hallucination.
"""
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.llm_output import PositionExtractionOutput
from app.utils.logger import get_logger
from app.utils.position_formatter import format_position_for_llm
from app.utils.llm_factory import get_llm
import chess

logger = get_logger(__name__)


class PositionExtractionAgent:
    """Agent for extracting piece positions from chess positions using LLM."""

    def __init__(self):
        """Initialize position extraction agent with OpenAI LLM."""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        logger.info(f"[AGENT] PositionExtractionAgent - Using OpenAI model: {settings.openai_model}")
        
        self.llm = get_llm(use_vision=False, require_primary=True)
        
        # Create structured output LLM using default json_schema method
        # (now compatible after restructuring schema to use nested models)
        self.structured_llm = self.llm.with_structured_output(PositionExtractionOutput)
        
        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a chess position verifier. Your task is to extract exact piece locations from the provided position representation.

**CRITICAL REQUIREMENTS:**
1. Extract piece locations with 100% accuracy
2. Use the piece list as the authoritative source
3. Cross-reference with ASCII board and FEN to ensure consistency
4. List ALL pieces on the board (no omissions)
5. Use exact square notation (e.g., "e1", "d5", "a7")

**OUTPUT FORMAT:**
- Group pieces by color (White/Black) and type (King, Queen, Rooks, Bishops, Knights, Pawns)
- For pieces that can have multiple instances (Rooks, Bishops, Knights, Pawns), list all squares
- For unique pieces (King, Queen), list the single square
- Identify the active color (who is to move)
- Note the square where the last piece moved to (if provided)
- Set confidence based on how well the representations match

**VERIFICATION:**
- If all three representations (ASCII board, FEN, piece list) match perfectly, set verification_status to "verified" and confidence to 1.0
- If there are any discrepancies, set verification_status to "needs_review" and lower confidence accordingly
- Always prioritize the piece list as the most reliable source

**EXAMPLE OUTPUT:**
{{
  "white_pieces": {{
    "King": ["e1"],
    "Queen": ["d1"],
    "Rooks": ["a1", "h1"],
    "Bishops": ["c1", "f1"],
    "Knights": ["b1", "g1"],
    "Pawns": ["a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2"]
  }},
  "black_pieces": {{
    "King": ["e8"],
    "Queen": ["d8"],
    "Rooks": ["a8", "h8"],
    "Bishops": ["c8", "f8"],
    "Knights": ["b8", "g8"],
    "Pawns": ["a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7"]
  }},
  "active_color": "White",
  "last_move_square": null,
  "verification_status": "verified",
  "confidence": 1.0
}}

Note: The output structure uses nested objects for white_pieces and black_pieces, with each containing King, Queen, Rooks, Bishops, Knights, and Pawns as arrays of square strings.""",
                ),
                (
                    "human",
                    """Extract piece positions from this chess position:

{position_representation}

{error_feedback}

{corrected_reference}

**INSTRUCTIONS:**
1. Read the piece list carefully - this is the AUTHORITATIVE source
2. Cross-check with ASCII board and FEN
3. Extract ALL pieces with their exact square locations
4. Identify active color (who is to move)
5. If last_move is provided, note the square where the piece moved to
6. Set confidence based on consistency across all three representations
7. If error feedback is provided above, carefully address those specific errors
8. If corrected reference is provided, use it as a guide but extract from the position representation

**CRITICAL: Use ONLY the piece locations shown in the piece list. Do not hallucinate or assume piece positions.**""",
                ),
            ]
        )
        
        # Create chain
        self.chain = self.prompt_template | self.structured_llm
        
        logger.info("[AGENT] PositionExtractionAgent initialized successfully")

    async def extract_position(
        self,
        fen: str,
        last_move: Optional[str] = None,
        highlight_squares: Optional[list] = None,
        error_feedback: Optional[str] = None,
        corrected_pieces: Optional[Dict[str, Dict[str, List[str]]]] = None,
    ) -> PositionExtractionOutput:
        """
        Extract piece positions from a chess position.

        Args:
            fen: FEN string of the position
            last_move: Optional last move in SAN notation (for context)
            highlight_squares: Optional squares to highlight
            error_feedback: Optional error feedback from previous validation attempt
            corrected_pieces: Optional corrected piece positions from validator

        Returns:
            PositionExtractionOutput with extracted piece positions
        """
        try:
            logger.debug(f"[AGENT] PositionExtractionAgent - Extracting position from FEN: {fen[:60]}...")
            
            # Format position representation (ASCII board + FEN + piece list)
            position_representation = format_position_for_llm(
                fen,
                last_move=last_move,
                highlight_squares=highlight_squares
            )
            
            # Add error feedback if provided (for retry attempts)
            feedback_section = ""
            if error_feedback:
                feedback_section = f"\n\n**PREVIOUS ATTEMPT ERRORS (Please correct these):**\n{error_feedback}\n\n**INSTRUCTIONS:**\n- Carefully review the errors above\n- Use the corrected piece positions provided below as reference\n- Extract positions accurately to avoid these errors\n"
            
            # Add corrected pieces reference if provided
            corrected_reference = ""
            if corrected_pieces:
                corrected_reference = "\n\n**REFERENCE - CORRECTED PIECE POSITIONS:**\n"
                corrected_reference += "White pieces:\n"
                for piece_type, squares in corrected_pieces.get("white", {}).items():
                    if squares:
                        corrected_reference += f"  {piece_type}: {', '.join(squares)}\n"
                corrected_reference += "\nBlack pieces:\n"
                for piece_type, squares in corrected_pieces.get("black", {}).items():
                    if squares:
                        corrected_reference += f"  {piece_type}: {', '.join(squares)}\n"
                corrected_reference += "\n**Use these as a reference, but extract from the position representation above.**\n"
            
            logger.debug(f"[AGENT] PositionExtractionAgent - Generated position representation (length: {len(position_representation)} chars)")
            if error_feedback:
                logger.info(f"[AGENT] PositionExtractionAgent - Retry attempt with error feedback ({len(error_feedback)} chars)")
            
            # Get Langfuse callback handler for tracing
            from app.utils.langfuse_handler import get_langfuse_handler
            langfuse_handler = get_langfuse_handler()
            
            # Invoke chain with structured output
            config = {}
            if langfuse_handler:
                config["callbacks"] = [langfuse_handler]
            
            logger.debug(f"[AGENT] PositionExtractionAgent - Invoking LLM for position extraction")
            result = await self.chain.ainvoke(
                {
                    "position_representation": position_representation,
                    "error_feedback": error_feedback or "",
                    "corrected_reference": corrected_reference,
                },
                config=config
            )
            
            logger.info(f"[AGENT] PositionExtractionAgent - Extraction complete: confidence={result.confidence}, status={result.verification_status}")
            logger.debug(f"[AGENT] PositionExtractionAgent - White pieces: {len(result.white_pieces.Pawns)} pawns, {len(result.white_pieces.Rooks)} rooks")
            logger.debug(f"[AGENT] PositionExtractionAgent - Black pieces: {len(result.black_pieces.Pawns)} pawns, {len(result.black_pieces.Rooks)} rooks")
            
            return result
            
        except Exception as e:
            logger.error(f"[AGENT] PositionExtractionAgent - Error extracting position: {e}", exc_info=True)
            raise ValueError(f"Failed to extract position from FEN: {e}") from e
