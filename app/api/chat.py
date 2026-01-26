"""
Chat API endpoints for game review chatbot.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
)
from app.agents.game_review_chatbot import GameReviewChatbotAgent
from app.services.chat_service import ChatService
from app.models.game import Game
from app.models.base import get_db
from sqlalchemy.orm import Session
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/games", tags=["chat"])

chat_service = ChatService()


@router.post("/{game_id}/chat", response_model=ChatMessageResponse)
async def chat_with_game(
    game_id: str,
    chat_request: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Chat with the game review chatbot.

    The chatbot answers questions about the reviewed game using cached analysis data.
    It cannot analyze new positions or call Stockfish.
    """
    # Verify game exists
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    try:
        # Get or create session
        session_id = chat_request.session_id
        if not session_id:
            session_id = chat_service.create_session(game_id)

        # Get conversation history
        history = chat_service.get_conversation_history(
            db=db,
            game_id=game_id,
            session_id=session_id,
            context_type="game",
            context_id=game_id,
        )

        # Initialize chatbot
        chatbot = GameReviewChatbotAgent()

        # Generate response
        result = await chatbot.chat(game_id, chat_request.message, history)

        # Save messages
        chat_service.add_message(
            db=db,
            game_id=game_id,
            session_id=session_id,
            role="user",
            content=chat_request.message,
            context_type="game",
            context_id=game_id,
        )
        chat_service.add_message(
            db=db,
            game_id=game_id,
            session_id=session_id,
            role="assistant",
            content=result["response"],
            context_type="game",
            context_id=game_id,
        )

        return ChatMessageResponse(
            response=result["response"],
            game_id=game_id,
            session_id=session_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}",
        )


@router.get("/{game_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    game_id: str,
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Get chat history for a specific session.

    Args:
        game_id: Unique game identifier
        session_id: Chat session identifier
    """
    # Verify game exists
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    try:
        history = chat_service.get_conversation_history(
            db=db,
            game_id=game_id,
            session_id=session_id,
            context_type="game",
            context_id=game_id,
        )
        return ChatHistoryResponse(
            game_id=game_id, session_id=session_id, messages=history
        )
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving chat history: {str(e)}",
        )
