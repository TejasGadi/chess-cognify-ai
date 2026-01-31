from typing import Dict, Any, List, Optional
import json
import re
import os
import base64
import httpx

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
            2. For each context block, check if an 'IMAGE_URL' is provided. 
            3. IF the context mentions specific chess moves, games, or positions that explain the concept:
               - You can output MULTIPLE chess data blocks if there are multiple relevant positions or variations to show.
               - Wrap EACH block in CHESS_DATA_JSON_START and CHESS_DATA_JSON_END.
               - If the context for a specific position contains an 'IMAGE_URL' field, you MUST prioritize including it in the JSON as "image_url".
               - ALWAYS provide a descriptive, professional title-case 'description' for each board (e.g., "The London System Setup").
               - Use Standard Algebraic Notation (SAN) for moves.
               - If a FEN is explicitly provided in context, use it.
            4. If no specific chess position is relevant, do not include any JSON blocks.
            
            Format your response as follows:
            [Your detailed text answer here...]
            
            CHESS_DATA_JSON_START
            {{
                "fen": "...", (optional, if a specific position is discussed)
                "pgn": "...", (optional, if a game or sequence is discussed)
                "moves": ["e4", "e5", ...], (optional, list of key moves mentioned)
                "image_url": "...", (REQUIRED if available in context)
                "description": "..." (Required, brief description of what this position represents)
            }}
            CHESS_DATA_JSON_END
            """
        )
        
        # Define Chain
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 10})
        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    async def query(self, user_query: str, book_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query using RAG with VLM-enhanced visual analysis.
        """
        try:
            logger.info(f"RAG Query: {user_query} (book_id: {book_id})")
            
            # Configure retriever with optional book_id filter
            search_kwargs = {"k": 10}
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
            
            # 1. Retrieve documents manually
            docs = await retriever.ainvoke(user_query)
            
            # 2. Extract unique image URLs from ALL retrieved chunks
            unique_image_urls = []
            for doc in docs:
                urls = doc.metadata.get("image_urls") or []
                if doc.metadata.get("image_url"): # Legacy support
                    urls.append(doc.metadata["image_url"])
                
                for url in urls:
                    if url not in unique_image_urls:
                        unique_image_urls.append(url)
            
            # 3. Get Visual Summaries from VLM for ALL unique images
            vlm_summaries_text = ""
            vlm_data_map = {}
            if unique_image_urls:
                vlm_data_map = await self._get_visual_summaries(unique_image_urls)
                if vlm_data_map:
                    vlm_summaries_text = "\n\nVISUAL DATA FROM BOOK DIAGRAMS:\n"
                    for i, (url, summary) in enumerate(vlm_data_map.items()):
                        vlm_summaries_text += f"[DIAGRAM {i+1}] (IMAGE_URL: {url})\nSUMMARY: {summary}\n\n"
            
            # 4. Format context for the prompt
            context_text = vlm_summaries_text + "\n\nTEXTUAL CONTENT FROM BOOK:\n"
            for i, doc in enumerate(docs):
                page = doc.metadata.get('page', 'Unknown')
                img_urls = doc.metadata.get('image_urls', [])
                if doc.metadata.get('image_url'):
                    img_urls.append(doc.metadata['image_url'])
                
                context_text += f"---\n[SOURCE {i+1}] (Page {page})\n"
                if img_urls:
                    context_text += f"ASSOCIATED_IMAGE_URLS: {', '.join(img_urls)}\n"
                context_text += f"CONTENT:\n{doc.page_content}\n---\n\n"
            
            # 5. Run the chain
            chain = (
                self.prompt
                | self.llm
                | StrOutputParser()
            )
            
            response_text = await chain.ainvoke({"context": context_text, "question": user_query})
            
            # Parse response
            answer, chess_data = self._parse_response(response_text)
            
            # Prepare detailed sources
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
                "images": unique_image_urls,
                "vlm_summaries": vlm_data_map, # Return map of URL -> Summary
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}", exc_info=True)
            return {
                "answer": "I created an error while processing your request. Please try again.",
                "status": "error",
                "error": str(e)
            }

    async def _get_visual_summaries(self, image_urls: List[str]) -> Dict[str, str]:
        """Use VLM (gpt-4o-mini) to extract detailed information from book images in parallel."""
        import asyncio
        
        # Create tasks for all images to run in parallel
        tasks = [self._analyze_single_image(url) for url in image_urls]
        results = await asyncio.gather(*tasks)
        
        # Merge results into a single dictionary (filtering out None)
        summaries = {}
        for res in results:
            if res:
                summaries.update(res)
        return summaries

    async def _analyze_single_image(self, url: str) -> Optional[Dict[str, str]]:
        """Helper to analyze a single image for parallel processing."""
        try:
            # Resolve local file path
            filename = url.replace("/api/book_images/", "")
            file_path = os.path.join("uploads/book_images", filename)
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call OpenAI Vision API (gpt-4o-mini)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Describe this chess diagram from a book. Identify the position, key pieces, and any tactical patterns or arrows shown. Be concise but technical."},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 300
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    summary = data['choices'][0]['message']['content']
                    return {url: summary}
                else:
                    logger.warning(f"VLM API failed for {url} with status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error in VLM analysis for {url}: {e}")
            
        return None

    def _parse_response(self, text: str) -> tuple[str, Optional[List[Dict[str, Any]]]]:
        """Extract all JSON blocks from response text."""
        matches = list(re.finditer(r"CHESS_DATA_JSON_START(.*?)CHESS_DATA_JSON_END", text, re.DOTALL))
        
        if not matches:
            return text.strip(), None
            
        chess_data_list = []
        clean_answer = text
        
        for match in matches:
            json_str = match.group(1).strip()
            # Remove the block from the text answer
            clean_answer = clean_answer.replace(match.group(0), "")
            try:
                data = json.loads(json_str)
                chess_data_list.append(data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse extracted JSON block: {json_str}")
                
        return clean_answer.strip(), chess_data_list if chess_data_list else None

# Global instance
rag_service = RagService()
