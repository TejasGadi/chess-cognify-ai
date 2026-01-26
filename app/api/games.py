"""
Game review API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from app.schemas.game import (
    GameCreate,
    GameResponse,
    GameReviewResponse,
    MoveReviewResponse,
    EngineAnalysisResponse,
    GameSummaryResponse,
)
from app.models.game import Game
from app.models.base import get_db
from app.agents.supervisor_agent import SupervisorAgent
from app.agents.state import GameReviewInput
from sqlalchemy.orm import Session
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("/upload", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def upload_game(game_data: GameCreate, db: Session = Depends(get_db)):
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


@router.post("/analyze", response_model=GameReviewResponse)
async def analyze_game(game_data: GameCreate):
    """
    Trigger complete game analysis workflow.

    This endpoint orchestrates the full review process:
    1. Validates PGN
    2. Runs Stockfish analysis
    3. Classifies moves
    4. Generates explanations
    5. Calculates accuracy and rating
    6. Detects weaknesses
    """
    try:
        supervisor = SupervisorAgent()
        input_data = GameReviewInput(
            pgn=game_data.pgn, metadata=game_data.metadata
        )

        review_output = await supervisor.review_game(input_data)

        if review_output.status == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=review_output.error or "Game analysis failed",
            )

        # Load complete review data
        from app.services.engine_analysis_service import EngineAnalysisService
        from app.services.move_classification_service import MoveClassificationService
        from app.models.base import SessionLocal

        db = SessionLocal()
        try:
            game = db.query(Game).filter(Game.game_id == review_output.game_id).first()
            if not game:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Game not found",
                )

            # Get move reviews
            from app.models.game import MoveReview

            move_reviews = (
                db.query(MoveReview)
                .filter(MoveReview.game_id == review_output.game_id)
                .order_by(MoveReview.ply)
                .all()
            )

            # Get summary
            from app.models.game import GameSummary

            summary = (
                db.query(GameSummary)
                .filter(GameSummary.game_id == review_output.game_id)
                .first()
            )

            # Check if analysis actually succeeded
            if not move_reviews or len(move_reviews) == 0:
                # No moves analyzed - this is an error
                error_msg = review_output.error or "Game analysis failed - no moves were analyzed"
                if "Stockfish" in error_msg or "stockfish" in error_msg.lower():
                    error_msg = "Stockfish engine not found. Please install Stockfish or set STOCKFISH_PATH in .env file."
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg,
                )
            
            # Also check if summary exists and has valid data
            if not summary:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Game analysis incomplete - summary not generated. Analysis may have failed.",
                )
            
            # Build moves list with move_san if available
            moves_list = []
            for r in move_reviews:
                move_dict = {
                    "ply": r.ply,
                    "label": r.label,
                    "centipawn_loss": r.centipawn_loss,
                    "explanation": r.explanation,
                    "accuracy": r.accuracy,
                }
                # Add move_san if the model has it
                if hasattr(r, 'move_san'):
                    move_dict["move_san"] = r.move_san
                moves_list.append(move_dict)

            return GameReviewResponse(
                game_id=review_output.game_id,
                game=GameResponse.model_validate(game),
                moves=moves_list,
                summary={
                    "accuracy": summary.accuracy if summary else 0,
                    "estimated_rating": summary.estimated_rating if summary else 400,
                    "rating_confidence": summary.rating_confidence if summary else "low",
                    "weaknesses": summary.weaknesses if summary and summary.weaknesses else [],
                },
            )
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing game: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing game: {str(e)}",
        )


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(game_id: str, db: Session = Depends(get_db)):
    """Get game details by ID."""
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )
    return game


@router.get("/{game_id}/review", response_model=GameReviewResponse)
async def get_game_review(game_id: str, db: Session = Depends(get_db)):
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

    summary = (
        db.query(GameSummary)
        .filter(GameSummary.game_id == game_id)
        .first()
    )

    return GameReviewResponse(
        game_id=game_id,
        game=GameResponse.model_validate(game),
        moves=[
            {
                "ply": r.ply,
                "label": r.label,
                "centipawn_loss": r.centipawn_loss,
                "explanation": r.explanation,
                "accuracy": r.accuracy,
            }
            for r in move_reviews
        ],
        summary={
            "accuracy": summary.accuracy if summary else None,
            "estimated_rating": summary.estimated_rating if summary else None,
            "rating_confidence": summary.rating_confidence if summary else None,
            "weaknesses": summary.weaknesses if summary else [],
        }
        if summary
        else None,
    )


@router.get("/{game_id}/moves", response_model=List[MoveReviewResponse])
async def get_game_moves(game_id: str, db: Session = Depends(get_db)):
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

    return [MoveReviewResponse.model_validate(r) for r in move_reviews]


@router.get("/{game_id}/summary", response_model=GameSummaryResponse)
async def get_game_summary(game_id: str, db: Session = Depends(get_db)):
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
async def get_game_analysis(game_id: str, db: Session = Depends(get_db)):
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
