"""
Book Chatbot Agent - RAG-based chatbot for answering questions about chess books.
"""
from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.config import settings
from app.services.vector_store_service import VectorStoreService
from app.utils.logger import get_logger
from app.utils.llm_factory import get_llm

logger = get_logger(__name__)


class BookChatbotAgent:
    """RAG-based chatbot for chess books."""

    def __init__(self):
        """Initialize book chatbot agent with OpenAI LLM."""
        self.llm = get_llm(use_vision=False, require_primary=True, allow_alternate=True)
        self.vector_store_service = VectorStoreService()

    def _get_rag_prompt(self, context_chunks: List[Dict], query: str) -> str:
        """
        Create RAG prompt with retrieved context.

        Args:
            context_chunks: List of retrieved document chunks
            query: User query

        Returns:
            Formatted prompt string
        """
        # Format context from chunks
        context_parts = []
        for idx, chunk in enumerate(context_chunks, 1):
            chunk_text = chunk["text"]
            metadata = chunk.get("metadata", {})
            source_info = f"[Source: {metadata.get('filename', 'Unknown')}"
            if "chunk_index" in metadata:
                source_info += f", Section {metadata['chunk_index'] + 1}"
            source_info += "]"

            context_parts.append(f"{idx}. {chunk_text}\n{source_info}")

        context_text = "\n\n".join(context_parts)

        prompt = f"""You are a helpful chess coach assistant. Answer questions about chess based on the provided book excerpts.

**Context from Chess Book:**
{context_text}

**User Question:** {query}

**Instructions:**
1. Answer the question based ONLY on the provided context excerpts.
2. If the context doesn't contain enough information, say so clearly.
3. Cite specific sources when referencing information (use the [Source: ...] tags).
4. Be concise but thorough.
5. Focus on chess concepts, strategies, and tactics.
6. If asked about something not in the context, politely explain that you can only answer based on the provided book excerpts.

**Answer:**"""

        return prompt

    def chat(
        self,
        query: str,
        book_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
    ) -> Dict[str, any]:
        """
        Answer a question about chess books using RAG.

        Args:
            query: User question
            book_id: Optional book ID to search within specific book
            conversation_history: Optional previous messages for context
            top_k: Number of context chunks to retrieve

        Returns:
            Dictionary with 'response', 'sources', and 'metadata'
        """
        try:
            # Retrieve relevant context
            logger.info(f"Searching vector store for query: {query[:50]}...")
            search_results = self.vector_store_service.search(
                query=query, book_id=book_id, top_k=top_k
            )

            if not search_results:
                return {
                    "response": "I couldn't find any relevant information in the available chess books. Please try rephrasing your question or ask about a different topic.",
                    "sources": [],
                    "metadata": {"book_id": book_id, "chunks_retrieved": 0},
                }

            # Prepare messages
            messages = []

            # Add system message with RAG context
            rag_prompt = self._get_rag_prompt(search_results, query)
            messages.append(SystemMessage(content=rag_prompt))

            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))

            # Add current query
            messages.append(HumanMessage(content=query))

            # Generate response
            logger.info("Generating response with LLM...")
            # Get Langfuse callback handler for tracing
            from app.utils.langfuse_handler import get_langfuse_handler
            langfuse_handler = get_langfuse_handler()
            
            # Pass Langfuse handler via config if available
            config = {}
            if langfuse_handler:
                config["callbacks"] = [langfuse_handler]
            
            response = self.llm.invoke(messages, config=config)

            # Extract sources
            sources = []
            for result in search_results:
                metadata = result.get("metadata", {})
                sources.append(
                    {
                        "filename": metadata.get("filename", "Unknown"),
                        "chunk_index": metadata.get("chunk_index"),
                        "score": result.get("score"),
                    }
                )

            # Log agent output
            logger.info(f"[AGENT] BookChatbotAgent - OUTPUT:")
            logger.info(f"[AGENT] BookChatbotAgent - User query: {query[:100]}...")
            logger.info(f"[AGENT] BookChatbotAgent - Response length: {len(response.content)} characters")
            logger.info(f"[AGENT] BookChatbotAgent - Response: {response.content}")
            logger.info(f"[AGENT] BookChatbotAgent - Sources retrieved: {len(sources)}")
            for i, source in enumerate(sources[:3], 1):
                logger.debug(f"[AGENT] BookChatbotAgent -   Source {i}: {source.get('filename', 'Unknown')} (score: {source.get('score', 'N/A')})")
            logger.debug(f"[AGENT] BookChatbotAgent - Full response: {response.content}")

            return {
                "response": response.content,
                "sources": sources,
                "metadata": {
                    "book_id": book_id,
                    "chunks_retrieved": len(search_results),
                    "top_score": search_results[0].get("score") if search_results else None,
                },
            }

        except Exception as e:
            logger.error(f"Error in book chatbot: {e}")
            return {
                "response": f"I encountered an error while processing your question: {str(e)}. Please try again.",
                "sources": [],
                "metadata": {"error": str(e)},
            }
