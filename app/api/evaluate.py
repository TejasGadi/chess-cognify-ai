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
    multipv: int = 1 # Number of lines to return


class TopMove(BaseModel):
    """Model for a single engine line."""
    move: str
    move_san: str
    eval: int
    eval_str: str
    rank: int
    pv_san: list[str] | None = None


class EvaluateResponse(BaseModel):
    """Response model for position evaluation."""
    fen: str
    eval_str: str  # e.g., "+1.23", "-0.45", "M3", "-M5"
    eval_cp: int  # Centipawn evaluation (positive = white advantage)
    best_move: str  # Best move in UCI format
    mate: int | None  # Mate in N moves (positive = white mates, negative = black mates)
    top_moves: list[TopMove] | None = None


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_position_endpoint(request: EvaluateRequest):
    """
    Evaluate a chess position using Stockfish engine.
    
    This endpoint provides LIVE evaluation (not from cached game analysis).
    
    Args:
        request: FEN position, optional depth, and optional multipv
        
    Returns:
        Evaluation data including centipawn score, best move, mate info, and optional top_moves
    """
    try:
        logger.info(f"[API] Live evaluation request for FEN: {request.fen[:50]}... depth={request.depth} multipv={request.multipv}")
        
        # Validate FEN and create Board
        import chess
        try:
            board = chess.Board(request.fen)
        except Exception as e:
            logger.error(f"[API] Invalid FEN: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid FEN: {str(e)}")
        
        # Get Stockfish service
        from app.services.stockfish_service import get_stockfish_service
        stockfish_service = await get_stockfish_service()
        
        if request.multipv > 1:
            # Multi-PV analysis
            logger.debug(f"[API] Getting top {request.multipv} moves with depth {request.depth}")
            top_moves_data = await stockfish_service.get_top_moves(
                board=board,
                top_n=request.multipv,
                depth=request.depth
            )
            
            if not top_moves_data:
                # Fallback if no moves found (e.g. checkmate)
                 return EvaluateResponse(
                    fen=request.fen,
                    eval_str="0.00",
                    eval_cp=0,
                    best_move="",
                    mate=None,
                    top_moves=[]
                )

            # Use the best move (rank 1) for the main stats
            best_line = top_moves_data[0]
            
            # Helper to check for mate in eval_str (e.g. "M3")
            mate = None
            if best_line["eval_str"].startswith("M") or best_line["eval_str"].startswith("-M"):
                 try:
                    mate = int(best_line["eval_str"].replace("M", ""))
                 except: 
                    pass
            
            return EvaluateResponse(
                fen=request.fen,
                eval_str=best_line["eval_str"],
                eval_cp=int(best_line["eval"]),
                best_move=best_line["move"],
                mate=mate,
                top_moves=[TopMove(**m) for m in top_moves_data]
            )
            
        else:
            # Single line evaluation (existing logic)
            logger.debug(f"[API] Evaluating position with depth {request.depth}")
            eval_result = await stockfish_service.evaluate_position(
                board=board,
                depth=request.depth
            )
            
            # Parse evaluation from StockfishService response
            eval_cp = eval_result.get("score", 0)
            score_str = eval_result.get("score_str", "0.00")
            
            # Check if it's a mate score
            mate = None
            if score_str.startswith("M") or score_str.startswith("-M"):
                try:
                    mate = int(score_str.replace("M", ""))
                except ValueError:
                    mate = None
            
            # Get best move from PV
            pv = eval_result.get("pv", [])
            best_move = ""
            if pv:
                try:
                    # pv is list of SAN strings in eval_result
                    best_move_san = pv[0]
                    move = board.parse_san(best_move_san)
                    best_move = move.uci()
                except Exception as _:
                    # As a fallback, maybe pv contained UCI? But service says SAN.
                    # Just in case logic in service changes or is mixed.
                    # If parse_san fails, we can try to see if it's already uci or just ignore.
                    # The service seems to try to convert to SAN, falling back to UCI. 
                    # So parse_san might fail if it's UCI.
                    # Let's rely on the service's robust return or just take it as is if parse fails?
                    # Ideally we want UCI for 'best_move'.
                    # Let's trust the service returns valid SAN or UCI.
                     best_move = pv[0] # Fallback
            
            return EvaluateResponse(
                fen=request.fen,
                eval_str=score_str,
                eval_cp=eval_cp,
                best_move=best_move,
                mate=mate,
                top_moves=None # Or we could construct a single TopMove if we wanted consistency
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error evaluating position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")

