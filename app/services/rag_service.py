from typing import Dict, Any, List, Optional, TypedDict
import json
import re
import os
import base64
import asyncio
import time

from openai import RateLimitError as OpenAIRateLimitError
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGState(TypedDict, total=False):
    """State schema for RAG LangGraph pipeline."""

    user_query: str
    book_id: Optional[str]
    docs: List[Any]
    unique_image_urls: List[str]
    relevant_image_urls: List[str]
    vlm_data_map: Dict[str, str]
    context_text: str
    response_text: str
    answer: str
    chess_data: Optional[List[Dict[str, Any]]]
    filtered_image_urls: List[str]
    filtered_vlm_map: Dict[str, str]
    sources: List[Dict[str, Any]]
    error: Optional[str]


class RelevantChunkIndices(BaseModel):
    """Pydantic schema for structured output: indices of chunks relevant to the user query."""

    indices: List[int] = Field(
        default_factory=list,
        description="Zero-based indices of document chunks that are relevant to answering the user query. Preserve order by relevance.",
    )


class RelevantImageURLs(BaseModel):
    """Pydantic schema for structured output: list of relevant image URLs to show in chat UI."""

    urls: List[str] = Field(default_factory=list, description="Image URLs that are directly relevant to the user question or answer.")


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
        
        # Initialize Embedding Model (retry on 429 rate limit)
        self.embedding_model = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
            max_retries=3,
        )
        
        # Initialize Vector Store
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection_name,
            embedding=self.embedding_model,
        )
        
        # Initialize LLM (retry on 429 rate limit)
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3,  # Slightly creative but grounded
            max_retries=3,
        )

        # Vision LLM for image analysis (LangChain ChatOpenAI)
        self.vision_llm = ChatOpenAI(
            model=settings.openai_vision_model,
            api_key=settings.openai_api_key,
            max_tokens=300,
            max_retries=3,
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

        # Build and compile LangGraph pipeline
        self.app = self._build_graph()

    def _build_graph(self):
        """Build LangGraph StateGraph with 8 nodes and linear edges. Returns compiled graph."""
        workflow = StateGraph(RAGState)

        workflow.add_node("retrieve", self._node_retrieve)
        workflow.add_node("extract_relevant_chunks", self._node_extract_relevant_chunks)
        workflow.add_node("extract_images", self._node_extract_images)
        workflow.add_node("extract_relevant_images", self._node_extract_relevant_images)
        workflow.add_node("vlm_summaries", self._node_vlm_summaries)
        workflow.add_node("format_context", self._node_format_context)
        workflow.add_node("generate_answer", self._node_generate_answer)
        workflow.add_node("parse_response", self._node_parse_response)
        workflow.add_node("filter_images", self._node_filter_images)
        workflow.add_node("build_output", self._node_build_output)

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "extract_relevant_chunks")
        workflow.add_edge("extract_relevant_chunks", "extract_images")
        workflow.add_edge("extract_images", "extract_relevant_images")
        workflow.add_edge("extract_relevant_images", "vlm_summaries")
        workflow.add_edge("vlm_summaries", "format_context")
        workflow.add_edge("format_context", "generate_answer")
        workflow.add_edge("generate_answer", "parse_response")
        workflow.add_edge("parse_response", "filter_images")
        workflow.add_edge("filter_images", "build_output")
        workflow.add_edge("build_output", END)

        return workflow.compile()

    async def _node_retrieve(self, state: RAGState) -> Dict[str, Any]:
        """Node: Configure retriever and run vector retrieval."""
        step_start = time.perf_counter()
        logger.info(f"[RAG] Step 1: Vector retrieval | query_preview={state.get('user_query', '')[:80]}...")
        search_kwargs: Dict[str, Any] = {"k": 15}
        if state.get("book_id"):
            search_kwargs["filter"] = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.book_id",
                        match=models.MatchValue(value=state["book_id"]),
                    )
                ]
            )
        logger.debug(f"[RAG] Step 1: search_kwargs k=15 book_id_filter={bool(state.get('book_id'))}")
        retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)
        docs = await retriever.ainvoke(state["user_query"])
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[RAG] Step 1: Vector retrieval | docs_retrieved={len(docs)} | time_ms={step_elapsed:.2f}")
        for idx, doc in enumerate(docs):
            page = doc.metadata.get("page", "?")
            bid = doc.metadata.get("book_id", "?")[:8] if doc.metadata.get("book_id") else "?"
            content_preview = (doc.page_content[:60] + "…") if len(doc.page_content) > 60 else doc.page_content
            logger.debug(f"[RAG]   doc[{idx}] page={page} book_id={bid} content_preview={content_preview!r}")
        return {"docs": docs}

    async def _node_extract_relevant_chunks(self, state: RAGState) -> Dict[str, Any]:
        """Node: Reranker / relevance checker — filter retrieved chunks to only those relevant to the query."""
        step_start = time.perf_counter()
        docs = state.get("docs") or []
        user_query = state.get("user_query") or ""
        if not docs:
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(f"[RAG] Step 1b: Extract relevant chunks | before=0 | after=0 | time_ms={step_elapsed:.2f}")
            return {"docs": []}
        candidates = "\n".join(
            f"[{i}] {doc.page_content[:300]}…" if len(doc.page_content) > 300 else f"[{i}] {doc.page_content}"
            for i, doc in enumerate(docs)
        )
        prompt = f"""You are a relevance filter for a chess book RAG system. The user asked a question. Below are document chunk excerpts with their zero-based index in brackets.

User question: {user_query[:400]}

Chunk excerpts (index then content):
{candidates}

Task: Which chunk indices are relevant to answering the user's question? Return only the indices that should be passed to the main LLM as context. Preserve order by relevance (most relevant first). Include at least 2 and at most 10 indices. If fewer than 10 are relevant, return only those."""

        try:
            structured_llm = self.llm.with_structured_output(RelevantChunkIndices)
            result: RelevantChunkIndices = await structured_llm.ainvoke(prompt)
            indices = [i for i in result.indices if 0 <= i < len(docs)]
            seen = set()
            unique_indices = []
            for i in indices:
                if i not in seen:
                    seen.add(i)
                    unique_indices.append(i)
            filtered_docs = [docs[i] for i in unique_indices]
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(
                f"[RAG] Step 1b: Extract relevant chunks | before={len(docs)} | after={len(filtered_docs)} | time_ms={step_elapsed:.2f}"
            )
            logger.debug(f"[RAG] Step 1b: kept indices={unique_indices}")
            return {"docs": filtered_docs}
        except Exception as e:
            logger.warning(f"[RAG] extract_relevant_chunks fallback to all docs | error={e}")
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(f"[RAG] Step 1b: Extract relevant chunks | before={len(docs)} | after={len(docs)} (fallback) | time_ms={step_elapsed:.2f}")
            return {"docs": docs}

    async def _node_extract_images(self, state: RAGState) -> Dict[str, Any]:
        """Node: Extract unique image URLs from retrieved docs."""
        step_start = time.perf_counter()
        docs = state.get("docs") or []
        unique_image_urls: List[str] = []
        for doc in docs:
            urls = doc.metadata.get("image_urls") or []
            if doc.metadata.get("image_url"):
                urls.append(doc.metadata["image_url"])
            for url in urls:
                if url not in unique_image_urls:
                    unique_image_urls.append(url)
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[RAG] Step 2: Image URL extraction | unique_images={len(unique_image_urls)} | time_ms={step_elapsed:.2f}")
        logger.debug(f"[RAG] Step 2: image_urls={unique_image_urls}")
        return {"unique_image_urls": unique_image_urls}

    async def _node_extract_relevant_images(self, state: RAGState) -> Dict[str, Any]:
        """Node: Relevance checker for images — filter image URLs to only those relevant to the query before VLM."""
        step_start = time.perf_counter()
        unique_image_urls = state.get("unique_image_urls") or []
        user_query = state.get("user_query") or ""
        if not unique_image_urls:
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(f"[RAG] Step 2b: Extract relevant images | before=0 | after=0 | time_ms={step_elapsed:.2f}")
            return {"relevant_image_urls": []}
        candidates_text = "\n".join(f"- {url}" for url in unique_image_urls)
        prompt = f"""You are a relevance filter for a chess book chat. The user asked a question. Below are image URLs that appear in the retrieved book chunks.

User question: {user_query[:400]}

Image URLs (from retrieved chunks):
{candidates_text}

Task: Which image URLs are likely relevant to answering the user's question? Return only the URLs that should be analyzed by the vision model and passed to the main LLM. Put them in the 'urls' field. If none are clearly relevant, return an empty list."""

        try:
            structured_llm = self.llm.with_structured_output(RelevantImageURLs)
            result: RelevantImageURLs = await structured_llm.ainvoke(prompt)
            relevant = [u for u in (result.urls or []) if u in unique_image_urls]
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(
                f"[RAG] Step 2b: Extract relevant images | before={len(unique_image_urls)} | after={len(relevant)} | time_ms={step_elapsed:.2f}"
            )
            logger.debug(f"[RAG] Step 2b: relevant_image_urls={relevant}")
            return {"relevant_image_urls": relevant}
        except Exception as e:
            logger.warning(f"[RAG] extract_relevant_images fallback to all | error={e}")
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(
                f"[RAG] Step 2b: Extract relevant images | before={len(unique_image_urls)} | after={len(unique_image_urls)} (fallback) | time_ms={step_elapsed:.2f}"
            )
            return {"relevant_image_urls": unique_image_urls}

    async def _node_vlm_summaries(self, state: RAGState) -> Dict[str, Any]:
        """Node: Get VLM summaries for relevant image URLs only."""
        step_start = time.perf_counter()
        relevant_image_urls = state.get("relevant_image_urls")
        if relevant_image_urls is None:
            relevant_image_urls = state.get("unique_image_urls") or []
        vlm_data_map: Dict[str, str] = {}
        if relevant_image_urls:
            vlm_data_map = await self._get_visual_summaries(relevant_image_urls)
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(f"[RAG] Step 3: VLM summaries | images_requested={len(relevant_image_urls)} | summaries_returned={len(vlm_data_map)} | time_ms={step_elapsed:.2f}")
            for url, summary in vlm_data_map.items():
                logger.debug(f"[RAG]   vlm url={url} summary_preview={summary[:80]!r}...")
        else:
            step_elapsed = (time.perf_counter() - step_start) * 1000
            logger.info(f"[RAG] Step 3: VLM summaries | skipped (no images) | time_ms={step_elapsed:.2f}")
        return {"vlm_data_map": vlm_data_map}

    async def _node_format_context(self, state: RAGState) -> Dict[str, Any]:
        """Node: Format context text for prompt from docs and VLM summaries."""
        step_start = time.perf_counter()
        docs = state.get("docs") or []
        vlm_data_map = state.get("vlm_data_map") or {}
        vlm_summaries_text = ""
        if vlm_data_map:
            vlm_summaries_text = "\n\nVISUAL DATA FROM BOOK DIAGRAMS:\n"
            for i, (url, summary) in enumerate(vlm_data_map.items()):
                vlm_summaries_text += f"[DIAGRAM {i+1}] (IMAGE_URL: {url})\nSUMMARY: {summary}\n\n"
        context_text = vlm_summaries_text + "\n\nTEXTUAL CONTENT FROM BOOK:\n"
        for i, doc in enumerate(docs):
            page = doc.metadata.get("page", "Unknown")
            img_urls = list(doc.metadata.get("image_urls") or [])
            if doc.metadata.get("image_url"):
                img_urls.append(doc.metadata["image_url"])
            context_text += f"---\n[SOURCE {i+1}] (Page {page})\n"
            if img_urls:
                context_text += f"ASSOCIATED_IMAGE_URLS: {', '.join(img_urls)}\n"
            context_text += f"CONTENT:\n{doc.page_content}\n---\n\n"
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[RAG] Step 4: Context formatting | context_chars={len(context_text)} | num_sources={len(docs)} | time_ms={step_elapsed:.2f}")
        logger.debug(f"[RAG] Step 4: context_preview={context_text[:200]!r}...")
        return {"context_text": context_text}

    async def _node_generate_answer(self, state: RAGState) -> Dict[str, Any]:
        """Node: Run LLM chain to generate response."""
        step_start = time.perf_counter()
        chain = self.prompt | self.llm | StrOutputParser()
        response_text = await chain.ainvoke(
            {"context": state["context_text"], "question": state["user_query"]}
        )
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[RAG] Step 5: LLM generation | response_chars={len(response_text)} | time_ms={step_elapsed:.2f}")
        logger.debug(f"[RAG] Step 5: response_preview={response_text[:200]!r}...")
        return {"response_text": response_text}

    async def _node_parse_response(self, state: RAGState) -> Dict[str, Any]:
        """Node: Parse response text into answer and chess_data."""
        step_start = time.perf_counter()
        answer, chess_data = self._parse_response(state.get("response_text") or "")
        step_elapsed = (time.perf_counter() - step_start) * 1000
        chess_count = len(chess_data) if chess_data else 0
        logger.info(f"[RAG] Step 6: Response parsing | chess_blocks={chess_count} | answer_chars={len(answer)} | time_ms={step_elapsed:.2f}")
        logger.debug(f"[RAG] Step 6: answer_preview={answer[:150]!r}...")
        return {"answer": answer, "chess_data": chess_data}

    async def _node_filter_images(self, state: RAGState) -> Dict[str, Any]:
        """Node: Filter images to only those relevant to query/answer (for UI display)."""
        step_start = time.perf_counter()
        # Candidate list: images we have VLM summaries for (relevant_image_urls) or all unique
        candidate_urls = state.get("relevant_image_urls")
        if candidate_urls is None:
            candidate_urls = state.get("unique_image_urls") or []
        relevant_from_filter = await self._filter_relevant_images(
            user_query=state["user_query"],
            answer=state.get("answer") or "",
            vlm_data_map=state.get("vlm_data_map") or {},
            chess_data=state.get("chess_data"),
            all_image_urls=candidate_urls,
        )
        filtered_image_urls = [u for u in candidate_urls if u in relevant_from_filter]
        filtered_vlm_map = {
            k: v
            for k, v in (state.get("vlm_data_map") or {}).items()
            if k in relevant_from_filter
        }
        step_elapsed = (time.perf_counter() - step_start) * 1000
        logger.info(f"[RAG] Step 7: Image filter | before={len(candidate_urls)} | after={len(filtered_image_urls)} | time_ms={step_elapsed:.2f}")
        logger.debug(f"[RAG] Step 7: filtered_image_urls={filtered_image_urls}")
        return {"filtered_image_urls": filtered_image_urls, "filtered_vlm_map": filtered_vlm_map}

    async def _node_build_output(self, state: RAGState) -> Dict[str, Any]:
        """Node: Build sources list for final response."""
        docs = state.get("docs") or []
        sources = [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in docs
        ]
        return {"sources": sources}

    async def query(self, user_query: str, book_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query using RAG with VLM-enhanced visual analysis.
        Retries on OpenAI 429 rate limit with backoff.
        """
        max_attempts = 3
        base_delay = 5.0  # seconds

        pipeline_start = time.perf_counter()
        logger.info(f"[RAG] Pipeline started | query_len={len(user_query)} | book_id={book_id}")

        initial_state: RAGState = {
            "user_query": user_query,
            "book_id": book_id,
            "docs": [],
            "unique_image_urls": [],
            "relevant_image_urls": [],
            "vlm_data_map": {},
            "context_text": "",
            "response_text": "",
            "answer": "",
            "chess_data": None,
            "filtered_image_urls": [],
            "filtered_vlm_map": {},
            "sources": [],
            "error": None,
        }

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"[RAG] Attempt {attempt}/{max_attempts} | query_preview={user_query[:80]}...")

                from app.utils.langfuse_handler import get_langfuse_handler
                langfuse_handler = get_langfuse_handler()
                config: Dict[str, Any] = {}
                if langfuse_handler:
                    config["callbacks"] = [langfuse_handler]

                final_state = await self.app.ainvoke(initial_state, config=config)

                total_elapsed = (time.perf_counter() - pipeline_start) * 1000
                sources = final_state.get("sources") or []
                filtered_image_urls = final_state.get("filtered_image_urls") or []
                logger.info(
                    f"[RAG] Pipeline completed | total_time_ms={total_elapsed:.2f} | sources={len(sources)} | images_shown={len(filtered_image_urls)} | status=success"
                )

                return {
                    "answer": final_state.get("answer") or "",
                    "chess_data": final_state.get("chess_data"),
                    "sources": sources,
                    "images": filtered_image_urls,
                    "vlm_summaries": final_state.get("filtered_vlm_map") or {},
                    "status": "success",
                }

            except OpenAIRateLimitError as e:
                total_elapsed = (time.perf_counter() - pipeline_start) * 1000
                if attempt == max_attempts:
                    logger.error(
                        f"[RAG] Pipeline failed (rate limit) | total_time_ms={total_elapsed:.2f} | attempts={max_attempts} | error={e}"
                    )
                    return {
                        "answer": "The service is busy (rate limit). Please wait a minute and try again.",
                        "status": "error",
                        "error": "rate_limit_exceeded",
                    }
                delay = base_delay * attempt
                logger.warning(
                    f"[RAG] Rate limit (429), retrying in {delay:.0f}s | attempt={attempt}/{max_attempts} | elapsed_ms={total_elapsed:.2f}"
                )
                await asyncio.sleep(delay)

            except Exception as e:
                total_elapsed = (time.perf_counter() - pipeline_start) * 1000
                logger.error(f"[RAG] Pipeline failed | total_time_ms={total_elapsed:.2f} | error={e}", exc_info=True)
                return {
                    "answer": "I encountered an error while processing your request. Please try again.",
                    "status": "error",
                    "error": str(e),
                }

    async def _get_visual_summaries(self, image_urls: List[str]) -> Dict[str, str]:
        """Use VLM (gpt-4o-mini) to extract detailed information from book images in parallel."""
        import asyncio

        logger.debug(f"[RAG] _get_visual_summaries: starting | num_images={len(image_urls)} | urls={image_urls[:3]}{'...' if len(image_urls) > 3 else ''}")
        start = time.perf_counter()

        tasks = [self._analyze_single_image(url) for url in image_urls]
        results = await asyncio.gather(*tasks)

        summaries = {}
        for res in results:
            if res:
                summaries.update(res)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"[RAG] _get_visual_summaries: done | summaries_returned={len(summaries)} | time_ms={elapsed_ms:.2f}")
        return summaries

    async def _filter_relevant_images(
        self,
        user_query: str,
        answer: str,
        vlm_data_map: Dict[str, str],
        chess_data: Optional[List[Dict[str, Any]]],
        all_image_urls: List[str],
    ) -> List[str]:
        """
        Filter image URLs to only those relevant to the user's question and the answer.
        Always includes images referenced in chess_data (model chose those). For the rest,
        uses LLM to decide relevance from VLM summaries. On error, returns all URLs.
        """
        if not all_image_urls:
            return []

        # Always include images that the model put in chess_data (explicitly relevant)
        from_chess = set()
        if chess_data:
            for block in chess_data:
                url = block.get("image_url") if isinstance(block, dict) else None
                if url and url in all_image_urls:
                    from_chess.add(url)

        if not vlm_data_map:
            return list(from_chess) if from_chess else all_image_urls

        # Build candidate list for LLM: url -> summary
        candidates_text = "\n".join(
            f"- URL: {url}\n  Description: {(vlm_data_map.get(url) or '')[:200]}"
            for url in all_image_urls
        )
        prompt = f"""You are a filter for a chess book chat UI. The user asked a question and received an answer. Below are image URLs from the book with short descriptions (from a vision model).

User question: {user_query[:500]}

Answer (excerpt): {answer[:800]}

Image candidates (URL and description):
{candidates_text}

Task: Which image URLs are DIRECTLY relevant to answering the user's question or are clearly referenced in the answer? Only include images that should be shown in the chat UI. Put them in the 'urls' field. If none are relevant, return an empty list."""

        try:
            structured_llm = self.llm.with_structured_output(RelevantImageURLs)
            result: RelevantImageURLs = await structured_llm.ainvoke(prompt)
            relevant = [u for u in (result.urls or []) if u in all_image_urls]
            # Merge with images from chess_data (always show those)
            result_list = list(dict.fromkeys(list(from_chess) + relevant))
            logger.debug(f"[RAG] _filter_relevant_images: from_chess={len(from_chess)} | from_llm={len(relevant)} | result={len(result_list)}")
            return result_list if result_list else all_image_urls  # fallback: show all if filter returned empty
        except Exception as e:
            logger.warning(f"[RAG] _filter_relevant_images: fallback to all images | error={e}")
            return all_image_urls

    async def _analyze_single_image(self, url: str) -> Optional[Dict[str, str]]:
        """Helper to analyze a single image using LangChain ChatOpenAI (vision)."""
        img_start = time.perf_counter()
        max_retries = 3
        base_delay = 5.0
        try:
            filename = url.replace("/api/book_images/", "")
            file_path = os.path.join("uploads/book_images", filename)

            if not os.path.exists(file_path):
                logger.debug(f"[RAG] _analyze_single_image: file not found | url={url} | path={file_path}")
                return None

            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            logger.debug(f"[RAG] _analyze_single_image: loaded | url={url} | base64_len={len(base64_image)}")

            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Describe this chess diagram from a book. Identify the position, key pieces, and any tactical patterns or arrows shown. Be concise but technical.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ]
            )

            for attempt in range(1, max_retries + 1):
                try:
                    response = await self.vision_llm.ainvoke([message])
                    summary = response.content if hasattr(response, "content") else str(response)
                    img_elapsed = (time.perf_counter() - img_start) * 1000
                    logger.debug(
                        f"[RAG] _analyze_single_image: success | url={url} | summary_len={len(summary)} | time_ms={img_elapsed:.2f}"
                    )
                    return {url: summary}
                except OpenAIRateLimitError as e:
                    if attempt == max_retries:
                        logger.warning(f"[RAG] _analyze_single_image: rate limit after {max_retries} attempts | url={url}")
                        return None
                    delay = base_delay * attempt
                    logger.warning(
                        f"[RAG] VLM rate limit (429) for {url}, retrying in {delay:.0f}s (attempt {attempt}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
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
