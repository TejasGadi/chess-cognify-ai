"""
Position Validator - Validates LLM-extracted positions against actual FEN.
Catches position hallucinations before explanation generation.
"""
from typing import List, Dict, Any
from dataclasses import dataclass
from app.schemas.llm_output import PositionExtractionOutput
from app.utils.logger import get_logger
import chess

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of position validation."""
    is_valid: bool
    discrepancies: List[str]
    confidence_score: float
    needs_revision: bool
    corrected_pieces: Dict[str, Dict[str, List[str]]]  # {"white": {...}, "black": {...}}


class PositionValidator:
    """Validates LLM-extracted positions against actual FEN positions."""

    # Piece names mapping
    PIECE_NAMES = {
        'K': 'King', 'Q': 'Queen', 'R': 'Rook', 'B': 'Bishop', 'N': 'Knight', 'P': 'Pawn',
        'k': 'King', 'q': 'Queen', 'r': 'Rook', 'b': 'Bishop', 'n': 'Knight', 'p': 'Pawn'
    }

    @staticmethod
    def _get_actual_pieces_from_fen(fen: str) -> Dict[str, Dict[str, List[str]]]:
        """
        Extract actual piece positions from FEN.

        Args:
            fen: FEN string

        Returns:
            Dictionary with actual piece positions: {"white": {...}, "black": {...}}
        """
        try:
            board = chess.Board(fen)
            
            white_pieces = {
                'King': [], 'Queen': [], 'Rooks': [], 'Bishops': [], 'Knights': [], 'Pawns': []
            }
            black_pieces = {
                'King': [], 'Queen': [], 'Rooks': [], 'Bishops': [], 'Knights': [], 'Pawns': []
            }
            
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece:
                    square_name = chess.square_name(square)
                    piece_name = PositionValidator.PIECE_NAMES.get(piece.symbol(), 'Unknown')
                    
                    if piece.color == chess.WHITE:
                        if piece_name == 'King':
                            white_pieces['King'].append(square_name)
                        elif piece_name == 'Queen':
                            white_pieces['Queen'].append(square_name)
                        elif piece_name == 'Rook':
                            white_pieces['Rooks'].append(square_name)
                        elif piece_name == 'Bishop':
                            white_pieces['Bishops'].append(square_name)
                        elif piece_name == 'Knight':
                            white_pieces['Knights'].append(square_name)
                        elif piece_name == 'Pawn':
                            white_pieces['Pawns'].append(square_name)
                    else:
                        if piece_name == 'King':
                            black_pieces['King'].append(square_name)
                        elif piece_name == 'Queen':
                            black_pieces['Queen'].append(square_name)
                        elif piece_name == 'Rook':
                            black_pieces['Rooks'].append(square_name)
                        elif piece_name == 'Bishop':
                            black_pieces['Bishops'].append(square_name)
                        elif piece_name == 'Knight':
                            black_pieces['Knights'].append(square_name)
                        elif piece_name == 'Pawn':
                            black_pieces['Pawns'].append(square_name)
            
            return {
                "white": white_pieces,
                "black": black_pieces
            }
        except Exception as e:
            logger.error(f"Error extracting pieces from FEN: {e}")
            raise

    @staticmethod
    def _normalize_piece_list(pieces) -> Dict[str, List[str]]:
        """
        Normalize piece list to ensure consistent format.
        Handles both singular and plural keys, and both dict and Pydantic models.

        Args:
            pieces: Piece dictionary from LLM extraction or PiecePositions model

        Returns:
            Normalized piece dictionary
        """
        # Convert Pydantic model to dict if needed
        if hasattr(pieces, 'model_dump'):
            pieces = pieces.model_dump()
        elif hasattr(pieces, 'dict'):
            pieces = pieces.dict()
        
        normalized = {
            'King': [],
            'Queen': [],
            'Rooks': [],
            'Bishops': [],
            'Knights': [],
            'Pawns': []
        }
        
        # Map possible variations
        key_mapping = {
            'King': ['King', 'Kings'],
            'Queen': ['Queen', 'Queens'],
            'Rooks': ['Rook', 'Rooks'],
            'Bishops': ['Bishop', 'Bishops'],
            'Knights': ['Knight', 'Knights'],
            'Pawns': ['Pawn', 'Pawns']
        }
        
        for standard_key, variations in key_mapping.items():
            for variation in variations:
                if variation in pieces:
                    value = pieces[variation]
                    if isinstance(value, list):
                        normalized[standard_key].extend(value)
                    # Remove duplicates and sort
                    normalized[standard_key] = sorted(list(set(normalized[standard_key])))
        
        return normalized

    @staticmethod
    def _compare_piece_lists(
        extracted: Dict[str, List[str]],
        actual: Dict[str, List[str]],
        color: str
    ) -> List[str]:
        """
        Compare extracted piece list with actual piece list.

        Args:
            extracted: LLM-extracted pieces
            actual: Actual pieces from FEN
            color: "white" or "black"

        Returns:
            List of discrepancy messages
        """
        discrepancies = []
        
        # Normalize extracted pieces
        extracted_normalized = PositionValidator._normalize_piece_list(extracted)
        
        # Compare each piece type
        for piece_type in ['King', 'Queen', 'Rooks', 'Bishops', 'Knights', 'Pawns']:
            extracted_squares = set(extracted_normalized.get(piece_type, []))
            actual_squares = set(actual.get(piece_type, []))
            
            # Find missing pieces (in actual but not in extracted)
            missing = actual_squares - extracted_squares
            if missing:
                for square in missing:
                    discrepancies.append(
                        f"LLM missed {color} {piece_type} on {square}"
                    )
            
            # Find hallucinated pieces (in extracted but not in actual)
            hallucinated = extracted_squares - actual_squares
            if hallucinated:
                for square in hallucinated:
                    discrepancies.append(
                        f"LLM hallucinated {color} {piece_type} on {square} (not in actual position)"
                    )
        
        return discrepancies

    @staticmethod
    def validate_extraction(
        extraction: PositionExtractionOutput,
        fen: str
    ) -> ValidationResult:
        """
        Validate LLM extraction against actual FEN position.

        Args:
            extraction: LLM-extracted position data
            fen: Actual FEN string to validate against

        Returns:
            ValidationResult with validation status and discrepancies
        """
        try:
            logger.debug(f"[VALIDATOR] Validating extraction against FEN: {fen[:60]}...")
            
            # Get actual pieces from FEN
            actual_pieces = PositionValidator._get_actual_pieces_from_fen(fen)
            
            # Convert PiecePositions models to dict for comparison
            white_pieces_dict = extraction.white_pieces.model_dump() if hasattr(extraction.white_pieces, 'model_dump') else extraction.white_pieces
            black_pieces_dict = extraction.black_pieces.model_dump() if hasattr(extraction.black_pieces, 'model_dump') else extraction.black_pieces
            
            # Compare white pieces
            white_discrepancies = PositionValidator._compare_piece_lists(
                white_pieces_dict,
                actual_pieces["white"],
                "white"
            )
            
            # Compare black pieces
            black_discrepancies = PositionValidator._compare_piece_lists(
                black_pieces_dict,
                actual_pieces["black"],
                "black"
            )
            
            # Check active color
            board = chess.Board(fen)
            actual_active_color = "White" if board.turn == chess.WHITE else "Black"
            color_discrepancy = None
            if extraction.active_color != actual_active_color:
                color_discrepancy = f"LLM says active color is {extraction.active_color}, actual: {actual_active_color}"
            
            # Combine all discrepancies
            all_discrepancies = white_discrepancies + black_discrepancies
            if color_discrepancy:
                all_discrepancies.append(color_discrepancy)
            
            # Calculate confidence score
            # Base confidence on number of discrepancies
            total_pieces = sum(len(pieces) for pieces in actual_pieces["white"].values()) + \
                          sum(len(pieces) for pieces in actual_pieces["black"].values())
            
            if total_pieces == 0:
                confidence_score = 0.0
            else:
                # Penalize for each discrepancy
                penalty = len(all_discrepancies) * 0.1
                confidence_score = max(0.0, min(1.0, 1.0 - penalty))
            
            # Determine if valid
            is_valid = len(all_discrepancies) == 0 and confidence_score >= 0.9
            
            # Determine if revision needed
            needs_revision = not is_valid or confidence_score < 0.8
            
            logger.info(
                f"[VALIDATOR] Validation complete: valid={is_valid}, "
                f"discrepancies={len(all_discrepancies)}, confidence={confidence_score:.2f}"
            )
            
            if all_discrepancies:
                logger.warning(f"[VALIDATOR] Found {len(all_discrepancies)} discrepancies:")
                for disc in all_discrepancies[:5]:  # Log first 5
                    logger.warning(f"[VALIDATOR]   - {disc}")
            
            return ValidationResult(
                is_valid=is_valid,
                discrepancies=all_discrepancies,
                confidence_score=confidence_score,
                needs_revision=needs_revision,
                corrected_pieces=actual_pieces
            )
            
        except Exception as e:
            logger.error(f"[VALIDATOR] Error validating extraction: {e}", exc_info=True)
            # Return invalid result on error
            return ValidationResult(
                is_valid=False,
                discrepancies=[f"Validation error: {str(e)}"],
                confidence_score=0.0,
                needs_revision=True,
                corrected_pieces={"white": {}, "black": {}}
            )
