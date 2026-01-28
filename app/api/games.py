"""
Game review API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List
from app.schemas.game import (
    GameCreate,
    GameUpdate,
    GameResponse,
    GameReviewResponse,
    MoveReviewResponse,
    EngineAnalysisResponse,
    GameSummaryResponse,
)
from app.models.game import Game, EngineAnalysis, MoveReview, GameSummary
from app.models.chat import ChatMessage
from app.models.base import get_db
from app.agents.supervisor_agent import SupervisorAgent
from app.agents.state import GameReviewInput
from sqlalchemy.orm import Session
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("/upload", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
def upload_game(game_data: GameCreate, db: Session = Depends(get_db)):
    """
    Upload a PGN game.

    Creates a game record and returns game_id.
    """
    try:
        import uuid

        game_id = str(uuid.uuid4())
        game = Game(game_id=game_id, pgn=game_data.pgn, game_metadata=game_data.metadata)
        db.add(game)
        db.commit()
        db.refresh(game)

        logger.info(f"Game uploaded: {game_id}")
        return game
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading game: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading game: {str(e)}",
        )


async def run_game_analysis(game_id: str, pgn: str, metadata: dict = None):
    """
    Background task to run the complete game analysis workflow.
    """
    from app.models.base import SessionLocal
    db = SessionLocal()
    try:
        # Update status to analyzing
        game = db.query(Game).filter(Game.game_id == game_id).first()
        if game:
            game.status = "analyzing"
            db.commit()

        supervisor = SupervisorAgent()
        input_data = GameReviewInput(
            pgn=pgn, metadata=metadata, game_id=game_id
        )

        review_output = await supervisor.review_game(input_data)

        if not review_output or review_output.status == "error":
            error_msg = getattr(review_output, 'error', "Unknown error during analysis") if review_output else "Analysis returned None"
            logger.error(f"Analysis failed for game {game_id}: {error_msg}")
            
            # Re-fetch game in fresh session to avoid detached state
            game = db.query(Game).filter(Game.game_id == game_id).first()
            if game:
                game.status = "failed"
                game.error_message = error_msg
                db.commit()
            return

        # Update game status based on review_output
        game = db.query(Game).filter(Game.game_id == game_id).first()
        if game:
            if review_output.status == "error":
                game.status = "failed"
                game.error_message = review_output.error
                logger.error(f"Analysis failed for game {game_id}: {review_output.error}")
            else:
                game.status = "completed"
                game.error_message = None
                logger.info(f"Analysis completed successfully for game {game_id}")
                
            db.commit()

    except Exception as e:
        logger.error(f"Unexpected error in background analysis for game {game_id}: {e}")
        game = db.query(Game).filter(Game.game_id == game_id).first()
        if game:
            game.status = "failed"
            game.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/analyze", response_model=GameResponse)
def analyze_game(game_data: GameCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger complete game analysis workflow in the background.
    """
    try:
        import uuid
        game_id = str(uuid.uuid4())
        
        # Create game record with status 'pending'
        game = Game(
            game_id=game_id, 
            pgn=game_data.pgn, 
            game_metadata=game_data.metadata,
            status="pending"
        )
        db.add(game)
        db.commit()
        db.refresh(game)

        # Start analysis in background
        background_tasks.add_task(
            run_game_analysis, 
            game_id=game_id, 
            pgn=game_data.pgn, 
            metadata=game_data.metadata
        )

        logger.info(f"Analysis started in background for game: {game_id}")
        return game

    except Exception as e:
        db.rollback()
        logger.error(f"Error starting background analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting analysis: {str(e)}",
        )

@router.get("", response_model=List[GameResponse])
def list_games(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all uploaded games.
    """
    games = db.query(Game).order_by(Game.created_at.desc()).offset(skip).limit(limit).all()
    return games


@router.patch("/{game_id}", response_model=GameResponse)
def update_game(
    game_id: str,
    game_update: GameUpdate,
    db: Session = Depends(get_db)
):
    """
    Update game metadata (e.g., rename analysis).
    """
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )
    
    if game_update.metadata is not None:
        # Update metadata - merge or replace?
        # For simplicity, we'll merge if it exists, or replace.
        # SQLAlchemy JSON updates can be tricky, re-assigning the dict works best.
        current_metadata = dict(game.game_metadata) if game.game_metadata else {}
        current_metadata.update(game_update.metadata)
        game.game_metadata = current_metadata
    
    db.commit()
    db.refresh(game)
    return game


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: str, db: Session = Depends(get_db)):
    """
    Delete a game and all associated analysis data.
    """
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )
    
    # Delete associated data
    # Note: If proper cascade is set up in DB, this might be automatic,
    # but explicit deletion is safer given we haven't checked the foreign key constraints fully.
    db.query(MoveReview).filter(MoveReview.game_id == game_id).delete()
    db.query(EngineAnalysis).filter(EngineAnalysis.game_id == game_id).delete()
    db.query(GameSummary).filter(GameSummary.game_id == game_id).delete()
    db.query(ChatMessage).filter(ChatMessage.game_id == game_id).delete()
    
    # Delete the game
    db.delete(game)
    db.commit()
    return None


@router.get("/{game_id}", response_model=GameResponse)
def get_game(game_id: str, db: Session = Depends(get_db)):
    """Get game details by ID."""
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )
    return game


@router.get("/{game_id}/review", response_model=GameReviewResponse)
def get_game_review(game_id: str, db: Session = Depends(get_db)):
    """Get complete game review."""
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    # Get move reviews
    from app.models.game import MoveReview, GameSummary

    move_reviews = (
        db.query(MoveReview)
        .filter(MoveReview.game_id == game_id)
        .order_by(MoveReview.ply)
        .all()
    )

    # Get all engine analyses for this game in one query
    engine_analyses = (
        db.query(EngineAnalysis)
        .filter(EngineAnalysis.game_id == game_id)
        .all()
    )
    # Map by ply for quick lookup
    engine_map = {ea.ply: ea for ea in engine_analyses}

    # Build enriched moves list
    moves_list = []
    for r in move_reviews:
        engine_analysis = engine_map.get(r.ply)
        
        move_dict = {
            "ply": r.ply,
            "label": r.label,
            "centipawn_loss": r.centipawn_loss,
            "explanation": r.explanation,
            "accuracy": r.accuracy,
        }
        
        if engine_analysis:
            move_dict["eval_after"] = engine_analysis.played_move_eval
            move_dict["top_moves"] = engine_analysis.top_moves
            
            # Convert played_move (UCI) to SAN for display
            if engine_analysis.played_move:
                try:
                    import chess
                    board = chess.Board(engine_analysis.fen)
                    move = chess.Move.from_uci(engine_analysis.played_move)
                    move_dict["move_san"] = board.san(move)
                except Exception as e:
                    logger.warning(f"Error converting move to SAN: {e}")
                    move_dict["move_san"] = engine_analysis.played_move
        
        moves_list.append(move_dict)

    summary = (
        db.query(GameSummary)
        .filter(GameSummary.game_id == game_id)
        .first()
    )

    return GameReviewResponse(
        game_id=game_id,
        game=GameResponse.model_validate(game),
        moves=moves_list,
        summary=summary,
    )


@router.get("/{game_id}/moves", response_model=List[MoveReviewResponse])
def get_game_moves(game_id: str, db: Session = Depends(get_db)):
    """
    Get move-by-move analysis for a game.

    Returns all moves with their classifications, evaluations, and explanations.
    """
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    from app.models.game import MoveReview

    move_reviews = (
        db.query(MoveReview)
        .filter(MoveReview.game_id == game_id)
        .order_by(MoveReview.ply)
        .all()
    )

    # Get all engine analyses for this game in one query
    engine_analyses = (
        db.query(EngineAnalysis)
        .filter(EngineAnalysis.game_id == game_id)
        .all()
    )
    # Map by ply for quick lookup
    engine_map = {ea.ply: ea for ea in engine_analyses}

    # Enrich move reviews with top moves data from engine analysis
    enriched_reviews = []
    for r in move_reviews:
        engine_analysis = engine_map.get(r.ply)
        
        review_dict = {
            "ply": r.ply,
            "label": r.label,
            "centipawn_loss": r.centipawn_loss,
            "explanation": r.explanation,
            "accuracy": r.accuracy,
        }
        
        # Add top moves and evaluation data
        if engine_analysis:
            # Convert played_move (UCI) to SAN for display
            if engine_analysis.played_move:
                try:
                    import chess
                    board = chess.Board(engine_analysis.fen)
                    move = chess.Move.from_uci(engine_analysis.played_move)
                    review_dict["move_san"] = board.san(move)
                except Exception as e:
                    logger.warning(f"Error converting move to SAN: {e}")
                    review_dict["move_san"] = engine_analysis.played_move  # Fallback to UCI
            
            if hasattr(engine_analysis, 'top_moves') and engine_analysis.top_moves:
                review_dict["top_moves"] = engine_analysis.top_moves
            if hasattr(engine_analysis, 'played_move_eval') and engine_analysis.played_move_eval:
                review_dict["eval_after"] = engine_analysis.played_move_eval
        
        enriched_reviews.append(MoveReviewResponse.model_validate(review_dict))
    
    return enriched_reviews


@router.get("/{game_id}/summary", response_model=GameSummaryResponse)
def get_game_summary(game_id: str, db: Session = Depends(get_db)):
    """
    Get game summary including accuracy, estimated rating, and weaknesses.

    Returns high-level statistics and analysis of the game.
    """
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    from app.models.game import GameSummary

    summary = (
        db.query(GameSummary)
        .filter(GameSummary.game_id == game_id)
        .first()
    )

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game summary not found. Please analyze the game first.",
        )

    return GameSummaryResponse.model_validate(summary)


@router.get("/{game_id}/analysis", response_model=List[EngineAnalysisResponse])
def get_game_analysis(game_id: str, db: Session = Depends(get_db)):
    """
    Get raw engine analysis for a game.

    Returns Stockfish evaluation data for each move.
    """
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    from app.models.game import EngineAnalysis

    analyses = (
        db.query(EngineAnalysis)
        .filter(EngineAnalysis.game_id == game_id)
        .order_by(EngineAnalysis.ply)
        .all()
    )

    return [EngineAnalysisResponse.model_validate(a) for a in analyses]
