from typing import Dict, Any, List, Optional
import json
import re

from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RagService:
    """
    RAG Service for querying the chess book knowledge base.
    Includes logic to extract chess positions (FEN/PGN) from the answer.
    """
    def __init__(self):
        # Initialize Qdrant Client (reusing connection logic)
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        
        # Initialize Embedding Model
        self.embedding_model = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key
        )
        
        # Initialize Vector Store
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection_name,
            embedding=self.embedding_model,
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3, # Slightly creative but grounded
        )
        
        # Define Prompt
        self.prompt = ChatPromptTemplate.from_template(
            """You are an expert chess coach and assistant. Use the following pieces of retrieved context from chess books to answer the user's question.
            
            Context:
            {context}
            
            User Question: {question}
            
            Instructions:
            1. Answer the question comprehensively based on the context.
            2. IF the context mentions specific chess moves, games, or positions that explain the concept:
               - You MUST output the specific chess data in a separate JSON block at the end of your response.
               - Used Standard Algebraic Notation (SAN) for moves.
               - If a FEN is explicitly provided in context, use it.
               - If a PGN or move sequence is provided, include it.
            3. If no specific chess position is relevant, do not include the JSON block.
            
            Format your response as follows:
            [Your detailed text answer here...]
            
            CHESS_DATA_JSON_START
            {{
                "fen": "...", (optional, if a specific position is discussed)
                "pgn": "...", (optional, if a game or sequence is discussed)
                "moves": ["e4", "e5", ...], (optional, list of key moves mentioned)
                "description": "..." (brief description of what this position represents)
            }}
            CHESS_DATA_JSON_END
            """
        )
        
        # Define Chain
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    async def query(self, user_query: str, book_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query using RAG.
        
        Args:
            user_query: The user's question
            book_id: Optional book ID to filter results to a specific book
            
        Returns:
            Dict containing the answer and optional chess data
        """
        try:
            logger.info(f"RAG Query: {user_query} (book_id: {book_id})")
            
            # Configure retriever with optional book_id filter
            search_kwargs = {"k": 5}
            if book_id:
                search_kwargs["filter"] = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.book_id",
                            match=models.MatchValue(value=book_id),
                        )
                    ]
                )
            
            retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)
            
            # 1. Retrieve documents manually to return them as sources
            docs = await retriever.ainvoke(user_query)
            
            # 2. Format context for the prompt
            context_text = "\n\n".join([doc.page_content for doc in docs])
            
            # 3. Use a simpler chain with the pre-retrieved context
            chain = (
                self.prompt
                | self.llm
                | StrOutputParser()
            )
            
            # Run the chain
            response_text = await chain.ainvoke({"context": context_text, "question": user_query})
            
            # Parse response to separate text and JSON
            answer, chess_data = self._parse_response(response_text)
            
            # Prepare sources
            sources = [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in docs
            ]
            
            return {
                "answer": answer,
                "chess_data": chess_data,
                "sources": sources,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}", exc_info=True)
            return {
                "answer": "I created an error while processing your request. Please try again.",
                "status": "error",
                "error": str(e)
            }

    def _parse_response(self, text: str) -> tuple[str, Optional[Dict[str, Any]]]:
        """Extract JSON block from response text."""
        json_match = re.search(r"CHESS_DATA_JSON_START(.*?)CHESS_DATA_JSON_END", text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1).strip()
            # Remove the block from the text answer
            clean_answer = text.replace(json_match.group(0), "").strip()
            try:
                chess_data = json.loads(json_str)
                return clean_answer, chess_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse extracted JSON: {json_str}")
                return text, None # Return full text if parse fails
        
        return text.strip(), None

# Global instance
rag_service = RagService()
