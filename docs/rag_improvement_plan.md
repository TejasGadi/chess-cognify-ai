# RAG Retrieval Pipeline — Improvement Plan

> **Scope:** Chat query (retrieval) pipeline accuracy improvements for Chess Cognify AI  
> **Primary file:** `app/services/rag_service.py`  
> **Supporting files:** `app/services/book_processor.py`, `app/config.py`, `app/utils/cache.py`, `app/models/book.py`

---

## Recommended Changes Summary

| # | Change | Type | LLM calls saved | Accuracy impact |
|---|--------|------|-----------------|-----------------|
| 1 | FEN/PGN validation with python-chess | Bug fix | 0 | Eliminates silent Chessground crashes |
| 2 | Remove redundant image-filter node 4 | Cleanup | −1 per query | Neutral (node 9 already does this better) |
| 3 | Redis result cache | Performance | −5 on cache hit | Neutral (same answer faster) |
| 4 | Increase VLM `max_tokens` 300 → 600 | Config | 0 | Medium (complete diagram descriptions) |
| 5 | Remove dead `self.chain` / `self.retriever` | Cleanup | 0 | Cleanliness |
| 6 | Cross-encoder reranker (local) | Accuracy | −1 (removes LLM reranker) | High |
| 7 | HyDE query embedding | Accuracy | +1 (new, parallel) | High |
| 8 | Multi-query expansion | Accuracy | +1 (new, parallel) | High |
| 9 | Conversation rolling summary | Accuracy | 0 | Medium (long sessions) |
| 10 | Hybrid BM25 + dense retrieval | Accuracy | 0 | Highest (chess notation) |
| 11 | Parent-child chunking (ingestion) | Accuracy | 0 | High (answer depth) |
| 12 | Contextual chunk enrichment (ingestion) | Accuracy | +1 per chunk at index time | High (cold queries) |
| 13 | Chess metadata tagging (ingestion) | Accuracy | 0 | Medium (topic filtering) |
| 14 | Semantic router | Accuracy | +1 lightweight | Medium (adaptive strategy) |
| 15 | Contextual compression | Accuracy | +1 per query | Medium (focused context) |
| 16 | Streaming answer generation | UX | 0 | High perceived performance |
| 17 | Faithfulness grounding score | Safety | +1 lightweight | Medium (user trust) |

---

## Implementation Phases

### Phase 1 — Zero-Risk Quick Wins
*No ingestion changes. No new dependencies. Deployable independently.*

### Phase 2 — Retrieval Accuracy (query-time only)
*New dependencies: `sentence-transformers`. No re-ingestion of books.*

### Phase 3 — Deep Accuracy (requires re-ingestion)
*Ingestion pipeline changes. Existing Qdrant collection must be rebuilt.*

---

## Phase 1 — Zero-Risk Quick Wins

**Goal:** Fix bugs, remove waste, improve reliability. Can ship today.

---

### Task 1.1 — FEN/PGN Validation

**File:** `app/services/rag_service.py` → `_node_parse_response`  
**Why:** Node 8 blindly trusts LLM-generated FEN/PGN strings. Invalid FENs crash Chessground on the frontend with a silent JS error.  
**Dependency:** `python-chess==1.999` (already in `requirements.txt`)

```python
# Add to rag_service.py
import chess
import chess.pgn
import io

def _validate_chess_block(self, block: dict) -> dict:
    """Validate FEN/PGN fields using python-chess. Drop invalid ones silently."""
    if fen := block.get("fen"):
        try:
            chess.Board(fen)
        except (ValueError, AttributeError):
            block["fen"] = None
            logger.warning(f"[RAG] Dropped invalid FEN: {fen[:60]}")

    if pgn := block.get("pgn"):
        try:
            game = chess.pgn.read_game(io.StringIO(pgn))
            if game is None:
                block["pgn"] = None
                logger.warning(f"[RAG] Dropped invalid PGN: {pgn[:60]}")
        except Exception:
            block["pgn"] = None
    return block
```

Call `_validate_chess_block` on each item in `chess_data` inside `_node_parse_response` before returning state.

---

### Task 1.2 — Remove Redundant Image-Filter Node 4

**File:** `app/services/rag_service.py`  
**Why:** Node 4 (`extract_relevant_images`) filters images using only image URLs + user query — no content signal. It uses a full LLM call with `RelevantImageURLs` structured output. Node 9 (`filter_images`) does the same work post-generation with richer signal (answer + VLM descriptions). Node 4 adds ~1–2s latency with no accuracy benefit.

**Change:**
1. Delete `_node_extract_relevant_images` method.
2. Remove `workflow.add_node("extract_relevant_images", ...)` from `_build_graph`.
3. Update edge: `extract_images` → `vlm_summaries` (skip node 4).
4. In `_node_vlm_summaries`, read from `unique_image_urls` instead of `relevant_image_urls`.

```python
# _build_graph — updated edges (Phase 1)
workflow.add_edge("extract_images", "vlm_summaries")   # was: → extract_relevant_images → vlm_summaries
```

**State field `relevant_image_urls` can be removed** from `RAGState` TypedDict.

---

### Task 1.3 — Redis Result Cache for RAG Queries

**File:** `app/services/rag_service.py`, `app/utils/cache.py`  
**Why:** Redis is running and fully configured (`redis_cache_ttl=86400`). The cache utility already exists in `app/utils/cache.py` but is only used for game analysis. Common chess coaching questions (e.g., "What is the Sicilian Defence?") asked repeatedly do a full 5-LLM-call pipeline each time.

**Cache key design:**
```python
import hashlib

def _rag_cache_key(book_id: str, query: str) -> str:
    normalised = query.strip().lower()
    payload = f"rag:{book_id}:{normalised}"
    return "rag:" + hashlib.sha256(payload.encode()).hexdigest()[:32]
```

**In `query()` method:**
```python
# Before pipeline invocation
cache_key = self._rag_cache_key(book_id or "all", user_query)
cached = get_from_cache(cache_key)
if cached:
    logger.info("[RAG] Cache hit — returning cached response")
    return cached

# After successful pipeline completion
set_to_cache(cache_key, result, ttl=settings.redis_cache_ttl)
```

**Note:** Do not cache results that contain `status: "error"`.

---

### Task 1.4 — Increase VLM `max_tokens` 300 → 600

**File:** `app/services/rag_service.py` → `__init__`  
**Why:** Chess diagrams often contain complex positions with multiple tactical themes (pin, discovered attack, en passant). 300 tokens regularly truncates the description mid-analysis. 600 tokens gives full coverage with minimal additional cost (~$0.0005 per image).

```python
# Before
self.vision_llm = ChatOpenAI(model=settings.openai_vision_model, max_tokens=300, ...)

# After
self.vision_llm = ChatOpenAI(model=settings.openai_vision_model, max_tokens=600, ...)
```

Optionally make this a config setting: `rag_vlm_max_tokens: int = 600` in `app/config.py`.

---

### Task 1.5 — Remove Dead Code

**File:** `app/services/rag_service.py`  
**What:** Lines 148–154 define `self.retriever` and `self.chain` (a simple LCEL chain). These are never called — the `query()` method always uses `self.app` (LangGraph). The `_build_graph` docstring also says "8 nodes" but the graph has 11.

```python
# DELETE these lines from __init__:
self.retriever = self.vector_store.as_retriever(search_kwargs={"k": settings.rag_retrieve_k})
self.chain = (
    {"context": self.retriever, "question": RunnablePassthrough()}
    | self.prompt
    | self.llm
    | StrOutputParser()
)
```

Also fix the docstring: `"""Build LangGraph StateGraph with 11 nodes..."""`

---

## Phase 2 — Retrieval Accuracy (Query-Time Only)

**Goal:** Improve what gets retrieved and how it is ranked without touching ingestion.  
**New dependency:** `sentence-transformers` (cross-encoder reranker, runs locally on CPU)

```bash
pip install sentence-transformers
```

Add to `requirements.txt`:
```
sentence-transformers>=3.0.0
```

---

### Task 2.1 — Cross-Encoder Reranker (replaces LLM reranker)

**File:** `app/services/rag_service.py` → `_node_extract_relevant_chunks`  
**Why:** The current LLM reranker truncates each chunk to 300 chars and uses a general-purpose LLM to judge relevance. A cross-encoder model is purpose-built for pairwise relevance scoring, runs in ~80ms locally, costs nothing, and sees the full chunk.

**Model choice:** `BAAI/bge-reranker-v2-m3` (multilingual, good for chess books in any language) or `cross-encoder/ms-marco-MiniLM-L-6-v2` (English-only, faster).

```python
# app/services/rag_service.py — add to __init__
from sentence_transformers import CrossEncoder

self.reranker = CrossEncoder(
    "BAAI/bge-reranker-v2-m3",
    max_length=512,
    device="cpu",   # switch to "cuda" if GPU available
)
```

```python
# Replace _node_extract_relevant_chunks with:
async def _node_extract_relevant_chunks(self, state: RAGState) -> Dict[str, Any]:
    """Node: Cross-encoder reranker — score and filter retrieved chunks."""
    step_start = time.perf_counter()
    docs = state.get("docs") or []
    user_query = state.get("user_query") or ""

    if not docs:
        return {"docs": []}

    # Score all (query, chunk) pairs
    pairs = [(user_query, doc.page_content) for doc in docs]
    scores = self.reranker.predict(pairs)  # returns float array

    # Attach scores and sort
    scored = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)

    # Keep top N (between filter_min and filter_max)
    top_n = min(settings.rag_filter_max_chunks, len(scored))
    top_n = max(settings.rag_filter_min_chunks, top_n)

    # Only keep chunks above minimum relevance threshold
    threshold = 0.1
    filtered = [(s, d) for s, d in scored[:top_n] if s > threshold]
    if not filtered:
        filtered = scored[:settings.rag_filter_min_chunks]  # always return at least min

    filtered_docs = [d for _, d in filtered]
    step_elapsed = (time.perf_counter() - step_start) * 1000
    logger.info(
        f"[RAG] Step 1b: Cross-encoder rerank | before={len(docs)} | after={len(filtered_docs)} | time_ms={step_elapsed:.2f}"
    )
    return {"docs": filtered_docs}
```

**Performance comparison:**

| | LLM Reranker (current) | Cross-Encoder (new) |
|---|---|---|
| Latency | ~1.5–3s | ~50–100ms |
| API cost | ~$0.002/query | $0 |
| Chunk preview | 300 chars | Full chunk (512 tokens) |
| Accuracy | General LLM | Purpose-built ranking model |

---

### Task 2.2 — HyDE (Hypothetical Document Embedding)

**File:** `app/services/rag_service.py` → `_node_retrieve`  
**Why:** Students ask in casual language ("how do I play against the e4 center?") while chess books use formal prose ("counteracting White's central pawn majority requires..."). Embedding a hypothetical formal answer bridges this vocabulary gap. Retrieval precision improves measurably on conceptual questions.

```python
# Add new helper method
async def _generate_hyde_embedding(self, user_query: str) -> Optional[List[float]]:
    """Generate HyDE embedding: embed a hypothetical book passage, not the raw query."""
    try:
        hyde_prompt = f"""Write a short 3-4 sentence passage from a chess book that would directly answer this question. 
Use formal chess book prose style with proper notation.
Question: {user_query}
Passage:"""
        response = await self.llm.ainvoke([HumanMessage(content=hyde_prompt)])
        hypothetical_passage = response.content.strip()
        logger.debug(f"[RAG] HyDE passage: {hypothetical_passage[:120]}")
        embedding = await self.embedding_model.aembed_query(hypothetical_passage)
        return embedding
    except Exception as e:
        logger.warning(f"[RAG] HyDE generation failed, falling back to query embedding | error={e}")
        return None
```

```python
# In _node_retrieve — blend HyDE vector with query vector
async def _node_retrieve(self, state: RAGState) -> Dict[str, Any]:
    search_query = state.get("search_query") or state.get("user_query") or ""
    user_query = state.get("user_query") or ""

    # Generate HyDE embedding in parallel with standard query embedding
    hyde_embedding, query_embedding = await asyncio.gather(
        self._generate_hyde_embedding(user_query),
        self.embedding_model.aembed_query(search_query),
        return_exceptions=True,
    )

    # Blend: average HyDE + query vectors if both available
    if isinstance(hyde_embedding, list) and isinstance(query_embedding, list):
        import numpy as np
        blended = list(np.mean([hyde_embedding, query_embedding], axis=0))
    else:
        blended = query_embedding if isinstance(query_embedding, list) else None

    # Use blended vector for Qdrant search
    # ... rest of retrieval logic using blended vector
```

**Note:** HyDE adds 1 LLM call but it runs concurrently with other setup, so wall-clock overhead is minimal.

---

### Task 2.3 — Multi-Query Expansion

**File:** `app/services/rag_service.py` → new node `_node_multi_query`  
**Why:** One query vector can miss relevant chunks if phrased differently from how the book writes about the topic. Three alternative phrasings retrieve from different directions; the union gives a richer candidate pool before reranking.

```python
async def _node_multi_query(self, state: RAGState) -> Dict[str, Any]:
    """Node: Generate 3 alternative phrasings for the user query."""
    user_query = state.get("user_query") or ""
    try:
        prompt = f"""Generate 3 different search queries to find relevant chess book passages for this question.
Each query should use different phrasing or focus on a different aspect.
Output one query per line, no numbering, no explanation.
Question: {user_query}"""
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        variants = [q.strip() for q in response.content.strip().splitlines() if q.strip()][:3]
    except Exception:
        variants = []

    all_queries = list({state.get("search_query") or user_query, *variants})
    logger.info(f"[RAG] Multi-query: {len(all_queries)} variants")
    return {"all_queries": all_queries}
```

In `_node_retrieve`, run Qdrant search for each query variant in parallel and deduplicate by `page_content` hash before passing to the reranker:

```python
# Run retrieval for all query variants in parallel
results_per_query = await asyncio.gather(*[
    retriever.ainvoke(q) for q in state["all_queries"]
])
# Deduplicate by content hash
seen, unique_docs = set(), []
for docs in results_per_query:
    for doc in docs:
        h = hashlib.md5(doc.page_content.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique_docs.append(doc)
```

Add `all_queries: List[str]` to `RAGState`.

---

### Task 2.4 — Conversation Rolling Summary

**File:** `app/services/rag_service.py`, `app/api/books.py`  
**Why:** `RAG_CHAT_HISTORY_LIMIT = 3` hard-discards all messages older than the last 3. A student spending 10 messages on the Nimzo-Indian loses all context by message 5. A rolling summary preserves the coaching arc.

**Config addition (`app/config.py`):**
```python
rag_chat_summary_threshold: int = 6   # summarise when session exceeds this many messages
rag_chat_summary_max_tokens: int = 100  # length of rolling summary
```

**New `ChatService` method (`app/services/chat_service.py`):**
```python
async def get_or_build_session_summary(
    self, db: Session, session_id: str, llm: ChatOpenAI
) -> Optional[str]:
    """Return existing summary or generate one if session is long enough."""
    all_messages = self.get_conversation_history(db, session_id)
    if len(all_messages) <= settings.rag_chat_summary_threshold:
        return None
    # Summarise all but the last 3
    older = all_messages[:-3]
    blob = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in older)
    prompt = f"Summarise this chess coaching conversation in 2 sentences. Focus on the chess topics covered.\n{blob}"
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return response.content.strip()
```

**In `_node_reformulate_query`:** Prepend the rolling summary to the history blob if available.

---

### Task 2.5 — Adaptive k Based on Query Type

**File:** `app/config.py`, `app/services/rag_service.py` → `_node_retrieve`  
**Why:** k=15 for every query wastes reranker time on simple factual lookups and may be too small for complex strategic questions.

**Config additions:**
```python
rag_retrieve_k_simple: int = 8    # e.g. "What is castling?"
rag_retrieve_k_standard: int = 15  # default (current)
rag_retrieve_k_complex: int = 25   # e.g. "Explain pawn breaks in isolated pawn positions"
```

**Heuristic in `_node_retrieve`:**
```python
query_len = len(user_query.split())
if query_len < 8:
    k = settings.rag_retrieve_k_simple
elif query_len > 20 or any(w in user_query.lower() for w in ["compare", "explain", "strategy", "plan", "why"]):
    k = settings.rag_retrieve_k_complex
else:
    k = settings.rag_retrieve_k_standard
```

---

## Phase 3 — Deep Accuracy (Requires Re-ingestion)

**Goal:** Fix the root cause — improve what gets stored, not just how it is queried.  
**Warning:** All changes in this phase require deleting the existing Qdrant collection and re-processing all uploaded books.

---

### Task 3.1 — Hybrid BM25 + Dense Retrieval

**Files:** `app/services/book_processor.py`, `app/services/rag_service.py`  
**Why:** Chess notation (`1.e4 e5`, `Nf6`, `Ruy Lopez Exchange`) is exact terminology. Dense cosine search returns semantically similar content (other Spanish game content) instead of the passage that literally contains the phrase. BM25 keyword matching is far superior for this domain.

**Qdrant sparse vector support (at ingestion):**

```python
# book_processor.py — when storing chunks, also compute sparse vectors
from qdrant_client.http.models import SparseVector

# Sparse tokenisation (simple BM25-style TF-IDF weights)
from sklearn.feature_extraction.text import TfidfVectorizer

# At BookProcessor.__init__:
self.tfidf = TfidfVectorizer(max_features=30000)

# After collecting all chunk texts, fit and transform:
chunk_texts = [doc.page_content for doc in final_splits]
sparse_matrix = self.tfidf.fit_transform(chunk_texts)

# When upserting to Qdrant, include both dense and sparse vectors per point.
```

**At query time (hybrid retrieval):**
```python
# rag_service.py — _node_retrieve
from qdrant_client.http.models import Prefetch, FusionQuery, Fusion, SparseVector

results = self.qdrant_client.query_points(
    collection_name=settings.qdrant_collection_name,
    prefetch=[
        Prefetch(query=dense_vector, using="dense", limit=k),
        Prefetch(query=SparseVector(indices=sparse_indices, values=sparse_values),
                 using="sparse", limit=k),
    ],
    query=FusionQuery(type=Fusion.RRF),
    limit=k,
    with_payload=True,
)
```

**Collection recreation required:** Add a new named vector config for `"sparse"` alongside `"dense"` in `_ensure_collection_exists`.

---

### Task 3.2 — Parent-Child Chunking

**File:** `app/services/book_processor.py`  
**Why:** 800-char chunks are precise for retrieval but too small for rich answers. Retrieving with small chunks and answering with large parent blocks gives both precision and depth.

**Two-tier storage:**

```
Parent block:  1500 chars → stored with parent_id = "{book_id}_{block_index}"
Child chunk:   300 chars  → stored with parent_id pointer in metadata
```

**At ingestion:**
```python
# Split into parents (1500 chars) first
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
parent_docs = parent_splitter.split_documents(processed_docs)

# Split parents into children (300 chars)
child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
for i, parent in enumerate(parent_docs):
    parent_id = f"{book_id}_parent_{i}"
    parent.metadata["parent_id"] = parent_id
    children = child_splitter.split_documents([parent])
    for child in children:
        child.metadata["parent_id"] = parent_id  # pointer back to parent

# Store only children in Qdrant (for retrieval)
# Store parents in a separate Qdrant collection OR in PostgreSQL as JSONB
vector_store.add_documents(children)
```

**At query time:**
```python
# After cross-encoder selects top child chunks, fetch their parent blocks
parent_ids = list({doc.metadata["parent_id"] for doc in top_child_docs})
parent_docs = self._fetch_parents(parent_ids)  # from PG or second Qdrant collection
# Pass parent_docs (not children) to format_context
```

---

### Task 3.3 — Contextual Chunk Enrichment at Ingestion

**File:** `app/services/book_processor.py`  
**Why:** A chunk reading *"The bishop on e3 coordinates well with the f2-f3 advance"* has no context about which opening or chapter this refers to. At query time, the embedding is blind to this context. Prepending a short LLM-generated context sentence makes every chunk self-contained.

```python
# At ingestion, after splitting, before storing:
async def _enrich_chunk(self, chunk: Document, book_title: str, chapter: str) -> Document:
    prompt = f"""Book: {book_title}. Chapter: {chapter}.
Given this excerpt, write ONE sentence of context (max 30 words) that describes what topic this passage covers.
Excerpt: {chunk.page_content[:400]}
Context sentence:"""
    response = await self.llm.ainvoke([HumanMessage(content=prompt)])
    context = response.content.strip()
    chunk.page_content = f"[Context: {context}]\n\n{chunk.page_content}"
    return chunk

# Process all chunks in batches with asyncio.gather (rate limit: max 10 concurrent)
sem = asyncio.Semaphore(10)
enriched = await asyncio.gather(*[_enrich_chunk(c, title, chapter) for c in chunks])
```

**Cost estimate:** For a 200-page book producing ~500 chunks, this is ~500 LLM calls (~$0.10 at gpt-4o-mini pricing). Use `gpt-4o-mini` (not `gpt-4o`) for this step.

---

### Task 3.4 — Chess Metadata Tagging at Ingestion

**File:** `app/services/book_processor.py`  
**Why:** Currently the only metadata filter is `book_id`. Tagging each chunk with chess-domain metadata enables structured retrieval (e.g., "retrieve only endgame chapters" or "filter by Sicilian opening").

```python
# Pydantic schema for structured tagging output
class ChessChunkMetadata(BaseModel):
    opening_name: Optional[str]   # "Ruy Lopez", "King's Indian", None
    phase: str                    # "opening" | "middlegame" | "endgame" | "general"
    themes: List[str]             # ["pawn structure", "king safety", "tactics"]

# At ingestion, after enrichment:
async def _tag_chunk(self, chunk: Document) -> Document:
    structured_llm = self.llm.with_structured_output(ChessChunkMetadata)
    tags = await structured_llm.ainvoke(
        f"Tag this chess book excerpt:\n{chunk.page_content[:500]}"
    )
    chunk.metadata.update({
        "opening_name": tags.opening_name,
        "phase": tags.phase,
        "themes": tags.themes,
    })
    return chunk
```

**At query time (semantic router uses these):**
```python
# Metadata filter in Qdrant: retrieve only endgame chunks
search_kwargs["filter"] = models.Filter(must=[
    models.FieldCondition(key="metadata.phase", match=models.MatchValue(value="endgame"))
])
```

**Qdrant schema:** Add `phase`, `opening_name`, `themes` to indexed payload fields.

---

### Task 3.5 — Semantic Router

**File:** `app/services/rag_service.py` → new node `_node_route_query`  
**Why:** Different query types benefit from different retrieval strategies. A tactical FEN query should route to Stockfish first, then RAG. A definitional question needs fewer chunks. A strategic question needs full parent blocks.

```python
class QueryRoute(BaseModel):
    query_type: str   # "factual" | "strategic" | "tactical" | "positional" | "opening"
    recommended_k: int
    use_hyde: bool
    use_metadata_filter: bool
    filter_phase: Optional[str]  # "opening" | "middlegame" | "endgame" | None

async def _node_route_query(self, state: RAGState) -> Dict[str, Any]:
    structured_llm = self.llm.with_structured_output(QueryRoute)
    route = await structured_llm.ainvoke(
        f"Classify this chess question for retrieval routing:\n{state['user_query']}"
    )
    return {"route": route.dict()}
```

Insert as first node (before reformulate), use `route` in `_node_retrieve` to set k, filters, and whether to run HyDE.

---

### Task 3.6 — Streaming Answer Generation

**File:** `app/api/books.py`, `app/services/rag_service.py`  
**Why:** The pipeline currently completes all 10 nodes before returning anything. With 5+ LLM calls this means 10–30 seconds of silence. Streaming node 7's output lets the user read the answer as it's generated.

**FastAPI endpoint change (`app/api/books.py`):**
```python
from fastapi.responses import StreamingResponse

@router.post("/{book_id}/query/stream")
async def query_book_stream(book_id: str, request: QueryRequest, db: Session = Depends(get_db)):
    async def event_generator():
        async for event in rag_service.stream_query(request.query, book_id):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**RagService streaming method:**
```python
async def stream_query(self, user_query: str, book_id: str):
    # Run nodes 0-6 normally (reformulate → retrieve → rerank → images → context)
    pre_state = await self._run_pre_generation_nodes(user_query, book_id)

    # Stream node 7 (generate_answer)
    chain = self.prompt | self.llm
    async for chunk in chain.astream({"context": pre_state["context_text"], "question": user_query}):
        yield {"type": "token", "content": chunk.content}

    # Run nodes 8-10 on full response (parse, filter, build)
    post_result = await self._run_post_generation_nodes(pre_state, full_response)
    yield {"type": "done", "chess_data": post_result["chess_data"], "sources": post_result["sources"]}
```

---

### Task 3.7 — Faithfulness Grounding Score

**File:** `app/services/rag_service.py` → new node `_node_faithfulness_check`  
**Why:** The LLM can elaborate beyond the book's content. A grounding score tells the UI whether to show a disclaimer.

```python
async def _node_faithfulness_check(self, state: RAGState) -> Dict[str, Any]:
    answer = state.get("answer") or ""
    docs = state.get("docs") or []
    if not answer or not docs:
        return {"faithfulness_score": 1.0}

    # Split answer into sentences and embed each
    sentences = [s.strip() for s in answer.split(".") if len(s.strip()) > 20]
    if not sentences:
        return {"faithfulness_score": 1.0}

    sentence_embeddings = await self.embedding_model.aembed_documents(sentences)
    doc_embeddings = await self.embedding_model.aembed_documents([d.page_content for d in docs])

    # For each answer sentence, find max cosine similarity to any source chunk
    import numpy as np
    doc_matrix = np.array(doc_embeddings)
    grounded = 0
    for sent_emb in sentence_embeddings:
        sent_vec = np.array(sent_emb)
        sims = doc_matrix @ sent_vec / (np.linalg.norm(doc_matrix, axis=1) * np.linalg.norm(sent_vec) + 1e-8)
        if sims.max() > 0.75:
            grounded += 1

    score = grounded / len(sentences)
    return {"faithfulness_score": round(score, 2)}
```

Return `faithfulness_score` in the API response. Frontend shows a subtle warning when score < 0.6.

---

## New Dependencies Summary

```
# requirements.txt additions

# Phase 2
sentence-transformers>=3.0.0   # cross-encoder reranker (Task 2.1)

# Phase 3
scikit-learn>=1.5.0            # TF-IDF sparse vectors for BM25 (Task 3.1)
```

No new infrastructure. All additions use existing PostgreSQL, Redis, and Qdrant.

---

## Config Additions (`app/config.py`)

```python
# RAG accuracy improvements
rag_vlm_max_tokens: int = 600
rag_retrieve_k_simple: int = 8
rag_retrieve_k_complex: int = 25
rag_chat_summary_threshold: int = 6
rag_chat_summary_max_tokens: int = 100
rag_reranker_model: str = "BAAI/bge-reranker-v2-m3"
rag_reranker_threshold: float = 0.1
rag_faithfulness_warn_threshold: float = 0.6
rag_hyde_enabled: bool = True
rag_multi_query_enabled: bool = True
rag_cache_enabled: bool = True
```

---

## Database Migration Requirements

### Phase 2
No schema changes.

### Phase 3 — Alembic Migration Required

```python
# alembic/versions/xxxx_rag_phase3.py
def upgrade():
    # Add chunk_type column to support parent/child distinction
    op.add_column("books", sa.Column("chunk_strategy", sa.String, nullable=True))
    # Add indexed_at to track re-ingestion
    op.add_column("books", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))
```

Qdrant collection must be **deleted and recreated** with:
- Named vectors: `"dense"` (1536d cosine) + `"sparse"` (sparse cosine)
- New indexed payload fields: `phase`, `opening_name`, `themes`, `parent_id`, `chunk_type`

---

## Execution Order

```
Phase 1 (independent, ship first):
  1.1 FEN/PGN validation          ← highest safety value
  1.5 Remove dead code            ← do first (cleaner base)
  1.2 Remove node 4               ← −1 LLM call, zero risk
  1.4 VLM max_tokens 600          ← one-liner
  1.3 Redis cache                 ← 1 day effort, high ROI

Phase 2 (after Phase 1, no re-ingestion):
  2.1 Cross-encoder reranker      ← highest accuracy gain in Phase 2
  2.5 Adaptive k                  ← simple, pairs well with 2.1
  2.4 Conversation summary        ← medium effort
  2.2 HyDE                        ← medium effort
  2.3 Multi-query                 ← medium effort

Phase 3 (plan for re-ingestion window):
  3.1 Hybrid BM25+dense           ← #1 accuracy gain overall
  3.2 Parent-child chunking       ← pairs with 3.1
  3.3 Contextual enrichment       ← highest per-chunk quality gain
  3.4 Chess metadata tagging      ← enables 3.5
  3.5 Semantic router             ← brings it all together
  3.6 Streaming                   ← UX, can ship independently
  3.7 Faithfulness score          ← last (needs stable pipeline)
```

---

## Expected Accuracy Impact by Phase

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| Exact notation retrieval | Poor | Poor | Moderate (HyDE) | High (BM25) |
| Conceptual question accuracy | Moderate | Moderate | High | Very High |
| Long session context quality | Poor (3-msg limit) | Poor | Good (summary) | Good |
| Answer faithfulness | Unknown | Validated FEN/PGN | Validated + scored | Validated + scored |
| Latency per query | ~15–30s | ~12–25s | ~6–12s | ~5–10s + streaming |
| Cost per query | ~$0.04 | ~$0.03 | ~$0.03 | ~$0.03 + ingestion |
