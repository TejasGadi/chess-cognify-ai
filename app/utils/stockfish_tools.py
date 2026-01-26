"""
Stockfish tools for LangChain agents - allows dynamic Stockfish analysis.
"""
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from app.services.stockfish_service import get_stockfish_service
from app.utils.logger import get_logger
from app.utils.fen_context import fen_context
import chess

logger = get_logger(__name__)


@tool
async def get_current_fen() -> Dict[str, Any]:
    """
    Get the current FEN positions from the analysis context.
    
    Use this tool to retrieve the stored FEN positions for the current move being analyzed.
    This prevents you from needing to remember or hallucinate FEN strings.
    
    Returns:
        Dictionary with:
        - fen_before: FEN position before the move
        - fen_after: FEN position after the move
        - played_move: Played move in UCI format
        - best_move: Best move in UCI format
        - played_move_san: Played move in SAN format
        - best_move_san: Best move in SAN format
        - error: Error message if context is not available
    """
    context = fen_context.get_context()
    if context:
        return {
            "fen_before": context["fen_before"],
            "fen_after": context["fen_after"],
            "played_move": context["played_move"],
            "best_move": context["best_move"],
            "played_move_san": context["played_move_san"],
            "best_move_san": context["best_move_san"],
        }
    else:
        return {
            "error": "No FEN context available. This tool should be used during move analysis.",
        }


@tool
async def analyze_position_deep(
    fen: Optional[str] = None, 
    depth: int = 20,
    include_pv: bool = True,
    use_context: bool = True
) -> Dict[str, Any]:
    """
    Analyze a chess position deeply with Stockfish engine.
    
    Use this tool when:
    - Evaluation shows significant issues (blunders, mistakes)
    - You need to understand why a position is bad
    - You need principal variation (PV) lines to explain tactics
    
    Args:
        fen: Position in FEN notation (optional - if None and use_context=True, uses fen_after from context)
        depth: Analysis depth (default: 20, higher = deeper but slower)
        include_pv: Whether to include principal variation lines
        use_context: If True and fen is None, use fen_after from context
    
    Returns:
        Dictionary with:
        - score: Evaluation in centipawns
        - score_str: Human-readable evaluation
        - pv: Principal variation (sequence of moves)
        - depth: Analysis depth reached
    """
    try:
        # Use context FEN if fen is not provided
        if fen is None and use_context:
            context = fen_context.get_context()
            if context:
                fen = context["fen_after"]
                logger.debug(f"Using context FEN for analyze_position_deep: {fen[:50]}...")
            else:
                return {
                    "error": "No FEN provided and no context available. Provide fen parameter or use get_current_fen() first.",
                    "score": 0,
                    "score_str": "Error",
                    "pv": [],
                    "depth": 0,
                }
        
        if fen is None:
            return {
                "error": "FEN parameter is required",
                "score": 0,
                "score_str": "Error",
                "pv": [],
                "depth": 0,
            }
        
        stockfish = await get_stockfish_service()
        board = chess.Board(fen)
        
        result = await stockfish.evaluate_position(board, depth=depth)
        
        return {
            "score": result["score"],
            "score_str": result["score_str"],
            "pv": result.get("pv", []) if include_pv else [],
            "depth": result.get("depth", depth),
        }
    except Exception as e:
        logger.error(f"Error in analyze_position_deep tool: {e}")
        return {
            "error": str(e),
            "score": 0,
            "score_str": "Error",
            "pv": [],
            "depth": 0,
        }


@tool
async def get_top_moves_analysis(
    fen: Optional[str] = None,
    top_n: int = 5,
    depth: int = 18,
    use_context: bool = True
) -> Dict[str, Any]:
    """
    Get top N moves for a position with their evaluations and PV lines.
    
    Use this tool when:
    - You need to compare multiple move alternatives
    - You want to see what the engine recommends
    - You need to understand why one move is better than others
    
    Args:
        fen: Position in FEN notation (optional - if None and use_context=True, uses fen_before from context)
        top_n: Number of top moves to return (default: 5)
        depth: Analysis depth (default: 18)
        use_context: If True and fen is None, use fen_before from context
    
    Returns:
        Dictionary with:
        - top_moves: List of top moves with evaluations and PV lines
    """
    try:
        # Use context FEN if fen is not provided
        if fen is None and use_context:
            context = fen_context.get_context()
            if context:
                fen = context["fen_before"]
                logger.debug(f"Using context FEN for get_top_moves_analysis: {fen[:50]}...")
            else:
                return {
                    "error": "No FEN provided and no context available. Provide fen parameter or use get_current_fen() first.",
                    "top_moves": [],
                    "position": "unknown",
                }
        
        if fen is None:
            return {
                "error": "FEN parameter is required",
                "top_moves": [],
                "position": "unknown",
            }
        
        stockfish = await get_stockfish_service()
        board = chess.Board(fen)
        
        top_moves = await stockfish.get_top_moves(board, top_n=top_n, depth=depth)
        
        return {
            "top_moves": top_moves,
            "position": fen,
        }
    except Exception as e:
        logger.error(f"Error in get_top_moves_analysis tool: {e}")
        return {
            "error": str(e),
            "top_moves": [],
            "position": fen,
        }


@tool
async def analyze_pv_line(
    fen: Optional[str] = None,
    move_sequence: Optional[List[str]] = None,
    depth: int = 20,
    use_context: bool = True
) -> Dict[str, Any]:
    """
    Analyze what happens after a specific sequence of moves.
    
    ⚠️ CRITICAL: This tool validates that all moves are legal in the starting position.
    If you get an error, check:
    1. The FEN matches the position you're analyzing
    2. The moves are legal from that FEN
    3. You're using the correct move format (UCI like "e2e4" or SAN like "e4")
    
    Use this tool when:
    - You need to understand what happens after a specific move sequence
    - You want to see the tactical consequences of a line
    - You need to explain why a sequence leads to a bad position
    
    Args:
        fen: Starting position in FEN notation (optional - if None and use_context=True, uses fen_before from context)
        move_sequence: List of moves in UCI format (e.g., ["e2e4", "e7e5"]) or SAN format (e.g., ["e4", "e5"])
                      If None and use_context=True, uses best_move from context
                      ALL moves MUST be legal from the starting FEN position
        depth: Analysis depth (default: 20)
        use_context: If True and fen/move_sequence are None, use values from context
    
    Returns:
        Dictionary with:
        - final_position: FEN after the sequence
        - evaluation: Final evaluation
        - material_changes: Material balance changes
        - tactical_issues: Detected tactical problems
        - error: Error message if moves are invalid (includes legal moves sample)
    """
    try:
        # Use context if parameters not provided
        if use_context:
            context = fen_context.get_context()
            if context:
                if fen is None:
                    fen = context["fen_before"]
                    logger.debug(f"Using context FEN for analyze_pv_line: {fen[:50]}...")
                if move_sequence is None:
                    # Default to analyzing best move sequence
                    move_sequence = [context["best_move"]]
                    logger.debug(f"Using context best_move for analyze_pv_line: {move_sequence}")
        
        if fen is None:
            return {
                "error": "FEN parameter is required. Use get_current_fen() to get the context FEN.",
                "moves_applied": [],
            }
        
        if move_sequence is None or len(move_sequence) == 0:
            return {
                "error": "move_sequence parameter is required",
                "moves_applied": [],
            }
        
        stockfish = await get_stockfish_service()
        board = chess.Board(fen)
        
        # Validate move sequence is not empty
        if not move_sequence:
            return {
                "error": "Move sequence is empty",
                "moves_applied": [],
            }
        
        # Apply move sequence
        moves_applied = []
        current_board = board.copy()
        
        for idx, move_str in enumerate(move_sequence):
            move_str = str(move_str).strip()
            if not move_str:
                continue
                
            move = None
            parse_error = None
            
            # Try UCI first (most reliable)
            try:
                move = chess.Move.from_uci(move_str)
                # Validate UCI move is legal
                if move not in current_board.legal_moves:
                    # Try to find similar legal moves
                    legal_uci_moves = [m.uci() for m in current_board.legal_moves]
                    logger.debug(f"Move '{move_str}' (UCI) not legal. Legal moves include: {legal_uci_moves[:5]}")
                    raise ValueError(f"Move '{move_str}' is not legal in position")
            except (ValueError, TypeError) as uci_error:
                # Try SAN parsing
                try:
                    move = current_board.parse_san(move_str)
                    # SAN parsing automatically checks legality, but double-check
                    if move not in current_board.legal_moves:
                        legal_san_moves = [current_board.san(m) for m in list(current_board.legal_moves)[:5]]
                        logger.debug(f"Move '{move_str}' (SAN) not legal. Legal moves include: {legal_san_moves[:5]}")
                        raise ValueError(f"Move '{move_str}' is not legal in position")
                except (ValueError, TypeError) as san_error:
                    parse_error = san_error
                    # Log with more context
                    legal_moves_sample = [current_board.san(m) for m in list(current_board.legal_moves)[:5]]
                    logger.warning(
                        f"Could not parse move '{move_str}' at index {idx} in position {current_board.fen()[:50]}... "
                        f"Legal moves include: {legal_moves_sample}. Error: {parse_error}"
                    )
                    return {
                        "error": f"Could not parse or validate move '{move_str}' at index {idx}",
                        "error_detail": str(parse_error),
                        "moves_applied": moves_applied,
                        "move_index": idx,
                        "position": current_board.fen(),
                        "legal_moves_sample": [current_board.san(m) for m in list(current_board.legal_moves)[:5]],
                    }
            
            # Move is valid, apply it
            try:
                move_san = current_board.san(move)
                current_board.push(move)
                moves_applied.append(move_san)
            except Exception as apply_error:
                logger.error(f"Failed to apply move '{move_str}' (parsed as {move}) even though it's legal: {apply_error}")
                return {
                    "error": f"Failed to apply move: {move_str}",
                    "error_detail": str(apply_error),
                    "moves_applied": moves_applied,
                    "position": current_board.fen(),
                    "move_index": idx,
                }
        
        # Analyze final position
        final_eval = await stockfish.evaluate_position(current_board, depth=depth)
        
        # Calculate material changes
        initial_material = _calculate_material(chess.Board(fen))
        final_material = _calculate_material(current_board)
        material_changes = {
            "white": final_material["white"] - initial_material["white"],
            "black": final_material["black"] - initial_material["black"],
        }
        
        # Detect tactical issues
        tactical_issues = _detect_tactical_issues(current_board)
        
        return {
            "final_position": current_board.fen(),
            "evaluation": final_eval["score_str"],
            "evaluation_cp": final_eval["score"],
            "pv": final_eval.get("pv", []),
            "moves_applied": moves_applied,
            "material_changes": material_changes,
            "tactical_issues": tactical_issues,
        }
    except Exception as e:
        logger.error(f"Error in analyze_pv_line tool: {e}", exc_info=True)
        return {
            "error": str(e),
            "moves_applied": [],
        }


@tool
async def detect_tactical_patterns(fen: Optional[str] = None, use_context: bool = True) -> Dict[str, Any]:
    """
    Detect tactical patterns in a position (pins, forks, discovered attacks, trapped pieces).
    
    Use this tool when:
    - Evaluation suggests tactics are present
    - You need to identify why a position is tactically dangerous
    - You want to explain tactical opportunities
    
    Args:
        fen: Position in FEN notation (optional - if None and use_context=True, uses fen_after from context)
        use_context: If True and fen is None, use fen_after from context
    
    Returns:
        Dictionary with detected tactical patterns
    """
    try:
        # Use context FEN if fen is not provided
        if fen is None and use_context:
            context = fen_context.get_context()
            if context:
                fen = context["fen_after"]
                logger.debug(f"Using context FEN for detect_tactical_patterns: {fen[:50]}...")
            else:
                return {
                    "error": "No FEN provided and no context available. Provide fen parameter or use get_current_fen() first.",
                    "tactical_patterns": [],
                    "position": "unknown",
                }
        
        if fen is None:
            return {
                "error": "FEN parameter is required",
                "tactical_patterns": [],
                "position": "unknown",
            }
        
        board = chess.Board(fen)
        patterns = _detect_tactical_issues(board)
        return {
            "position": fen,
            "tactical_patterns": patterns,
        }
    except Exception as e:
        logger.error(f"Error in detect_tactical_patterns tool: {e}")
        return {
            "error": str(e),
            "tactical_patterns": [],
        }


def _calculate_material(board: chess.Board) -> Dict[str, int]:
    """Calculate material balance for a position."""
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }
    
    white_material = 0
    black_material = 0
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            value = piece_values.get(piece.piece_type, 0)
            if piece.color == chess.WHITE:
                white_material += value
            else:
                black_material += value
    
    return {
        "white": white_material,
        "black": black_material,
    }


def _detect_tactical_issues(board: chess.Board) -> List[Dict[str, Any]]:
    """
    Detect tactical patterns in a position.
    Returns list of detected issues.
    """
    issues = []
    
    # Check for pinned pieces
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            # Check if piece is pinned
            if board.is_pinned(piece.color, square):
                issues.append({
                    "type": "pin",
                    "piece": board.san(chess.Move(square, square)),  # Placeholder
                    "square": chess.square_name(square),
                })
    
    # Check for trapped pieces (pieces with no legal moves)
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.piece_type != chess.KING:
            legal_moves = [m for m in board.legal_moves if m.from_square == square]
            if len(legal_moves) == 0:
                # Check if piece can be captured
                attackers = board.attackers(not piece.color, square)
                if len(attackers) > 0:
                    issues.append({
                        "type": "trapped_piece",
                        "piece": piece.symbol(),
                        "square": chess.square_name(square),
                        "attackers": len(attackers),
                    })
    
    # Check for back rank weaknesses
    if board.turn == chess.WHITE:
        back_rank = chess.BB_RANK_1
    else:
        back_rank = chess.BB_RANK_8
    
    king_square = board.king(board.turn)
    if king_square and chess.BB_SQUARES[king_square] & back_rank:
        # Check if king is on back rank with few escape squares
        escape_squares = [m.to_square for m in board.legal_moves if m.from_square == king_square]
        if len(escape_squares) <= 2:
            issues.append({
                "type": "back_rank_weakness",
                "color": "white" if board.turn == chess.WHITE else "black",
            })
    
    return issues
