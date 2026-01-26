"""
Chat service for managing conversation history.
"""
from typing import List, Dict, Any, Optional
from app.models.chat import ChatMessage
from app.models.base import SessionLocal
from app.utils.logger import get_logger
import uuid

logger = get_logger(__name__)


class ChatService:
    """Service for managing chat conversations."""

    def create_session_id(self) -> str:
        """
        Create a new chat session ID.

        Returns:
            Session ID
        """
        return str(uuid.uuid4())

    def create_session(self, game_id: str) -> str:
        """
        Create a new chat session (legacy method for game chats).

        Args:
            game_id: Unique game identifier

        Returns:
            Session ID
        """
        return self.create_session_id()

    def add_message(
        self,
        db,
        game_id: Optional[str],
        session_id: str,
        role: str,
        content: str,
        context_type: Optional[str] = None,
        context_id: Optional[str] = None,
    ) -> None:
        """
        Save a chat message to database.

        Args:
            db: Database session
            game_id: Optional game identifier (for backward compatibility)
            session_id: Chat session identifier
            role: Message role ("user" or "assistant")
            content: Message content
            context_type: "game" or "book"
            context_id: game_id or book_id depending on context_type
        """
        try:
            # Determine context_type and context_id
            if context_type is None:
                if game_id:
                    context_type = "game"
                    context_id = game_id
                else:
                    context_type = "book"
                    context_id = context_id

            message = ChatMessage(
                game_id=game_id,
                session_id=session_id,
                role=role,
                content=content,
                context_type=context_type,
                context_id=context_id,
            )
            db.add(message)
            db.commit()
            logger.debug(
                f"Saved {role} message for {context_type} {context_id}, session {session_id}"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving message: {e}")
            raise

    def save_message(
        self, game_id: str, session_id: str, role: str, content: str
    ) -> None:
        """
        Save a chat message to database (legacy method for game chats).

        Args:
            game_id: Unique game identifier
            session_id: Chat session identifier
            role: Message role ("user" or "assistant")
            content: Message content
        """
        db = SessionLocal()
        try:
            self.add_message(
                db=db,
                game_id=game_id,
                session_id=session_id,
                role=role,
                content=content,
                context_type="game",
                context_id=game_id,
            )
        finally:
            db.close()

    def get_conversation_history(
        self,
        db,
        game_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context_type: Optional[str] = None,
        context_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for a session.

        Args:
            db: Database session
            game_id: Optional game identifier (for backward compatibility)
            session_id: Chat session identifier
            context_type: "game" or "book"
            context_id: game_id or book_id depending on context_type
            limit: Optional limit on number of messages

        Returns:
            List of messages in format [{"role": "user/assistant", "content": "..."}]
        """
        try:
            query = db.query(ChatMessage)

            # Build filters
            if session_id:
                query = query.filter(ChatMessage.session_id == session_id)

            if context_type and context_id:
                query = query.filter(
                    ChatMessage.context_type == context_type,
                    ChatMessage.context_id == context_id,
                )
            elif game_id:
                # Legacy: filter by game_id
                query = query.filter(ChatMessage.game_id == game_id)

            query = query.order_by(ChatMessage.created_at)

            if limit:
                query = query.limit(limit)

            messages = query.all()

            return [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    def get_all_sessions(self, game_id: str) -> List[str]:
        """
        Get all session IDs for a game.

        Args:
            game_id: Unique game identifier

        Returns:
            List of session IDs
        """
        db = SessionLocal()
        try:
            sessions = (
                db.query(ChatMessage.session_id)
                .filter(ChatMessage.game_id == game_id)
                .distinct()
                .all()
            )
            return [s[0] for s in sessions]
        finally:
            db.close()
