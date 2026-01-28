"""
Live Position Evaluation API.
Provides real-time Stockfish evaluation for any FEN position.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.stockfish_service import StockfishService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["evaluation"])


class EvaluateRequest(BaseModel):
    """Request model for position evaluation."""
    fen: str
    depth: int = 15  # Default depth for live evaluation


class EvaluateResponse(BaseModel):
    """Response model for position evaluation."""
    fen: str
    eval_str: str  # e.g., "+1.23", "-0.45", "M3", "-M5"
    eval_cp: int  # Centipawn evaluation (positive = white advantage)
    best_move: str  # Best move in UCI format
    mate: int | None  # Mate in N moves (positive = white mates, negative = black mates)


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_position_endpoint(request: EvaluateRequest):
    """
    Evaluate a chess position using Stockfish engine.
    
    This endpoint provides LIVE evaluation (not from cached game analysis).
    
    Args:
        request: FEN position and optional depth
        
    Returns:
        Evaluation data including centipawn score, best move, and mate info
    """
    try:
        logger.info(f"[API] Live evaluation request for FEN: {request.fen[:50]}...")
        
        # Validate FEN and create Board
        import chess
        try:
            board = chess.Board(request.fen)
        except Exception as e:
            logger.error(f"[API] Invalid FEN: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid FEN: {str(e)}")
        
        # Get Stockfish service
        stockfish_service = StockfishService()
        
        # Evaluate position
        logger.debug(f"[API] Evaluating position with depth {request.depth}")
        eval_result = await stockfish_service.evaluate_position(
            board=board,
            depth=request.depth
        )
        
        # Parse evaluation from StockfishService response
        # eval_result has: {"score": centipawns, "score_str": "+1.23", "depth": 15, "pv": [...]}
        eval_cp = eval_result.get("score", 0)
        score_str = eval_result.get("score_str", "0.00")
        
        # Check if it's a mate score
        mate = None
        if score_str.startswith("M") or score_str.startswith("-M"):
            # Extract mate number from score_str (e.g., "M3" -> 3, "-M5" -> -5)
            try:
                mate = int(score_str.replace("M", ""))
            except ValueError:
                mate = None
        
        # Get best move from PV
        pv = eval_result.get("pv", [])
        best_move = ""
        if pv:
            # Convert first PV move (SAN) back to UCI
            try:
                best_move_san = pv[0]
                # Parse SAN move to get UCI
                move = board.parse_san(best_move_san)
                best_move = move.uci()
            except Exception as e:
                logger.warning(f"[API] Could not convert PV to UCI: {e}")
                best_move = pv[0]  # Fallback to SAN
        
        logger.info(f"[API] Evaluation complete: {score_str}, best move: {best_move}")
        
        return EvaluateResponse(
            fen=request.fen,
            eval_str=score_str,
            eval_cp=eval_cp,
            best_move=best_move,
            mate=mate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error evaluating position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")
