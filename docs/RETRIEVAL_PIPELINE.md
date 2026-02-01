# RAG Retrieval Pipeline – Chunk Counts & Full Explanation

## How many chunks are retrieved?

All counts are **configurable** via `app/config.py` (env vars below). Defaults:

| Stage | Default | Config (env) |
|-------|--------|--------------|
| **1. Vector retrieval** | **15** | `RAG_RETRIEVE_K` (5–50) |
| **2. After relevance filter** | **2–10** | `RAG_FILTER_MIN_CHUNKS` (1–20), `RAG_FILTER_MAX_CHUNKS` (2–20) |
| **3. Sent to LLM / in context** | **2–10** | Same as step 2 |
| **4. Returned as “sources”** | **2–10** | Same list; this is what the UI shows as citations |

So by default:

- **15 chunks** are fetched from the vector store per query.
- **2–10 of those** are kept after the relevance step and used for the answer and sources.

---

## Ingestion: how chunks are created (book processing)

Before any retrieval, the book is processed and split into chunks:

- **Location:** `app/services/book_processor.py`
- **Splitter:** `RecursiveCharacterTextSplitter`
  - **chunk_size:** 800 characters  
  - **chunk_overlap:** 200 characters  
- **Result:** Many chunks per book (stored in Qdrant). `book.total_chunks` holds the count for that book.

So at **ingestion** you have:

- One collection (e.g. `settings.qdrant_collection_name`).
- Many chunks per book (variable; depends on book length).
- Each chunk is a document with `page_content` and `metadata` (e.g. `book_id`, `page`, `chunk_index`, `image_url` / `image_urls`).

---

## Query reformulation (chat history, backend-handled)

Before retrieval, the user query can be **reformulated** using the **last 3 messages** of the conversation so that follow-ups (e.g. “What about the Sicilian?”) become standalone search queries. Chat history is **handled on the backend** (not sent from the frontend):

- **API:** `POST /api/books/{book_id}/query` accepts optional `session_id`. If missing, the backend creates one and returns it. The backend loads the last 3 messages for that `(book_id, session_id)` from the DB and passes them to the RAG pipeline.
- **Storage:** Messages are stored in `chat_messages` with `context_type="book"`, `context_id=book_id`, and `session_id`. `ChatService.get_recent_conversation_history(..., limit=3)` returns the last 3 messages in chronological order.
- **Pipeline:** The LangGraph state includes `chat_history` (last 3 messages) and `search_query` (reformulated query). The **reformulate_query** node runs first: if there is history, an LLM turns “current user message + last 3 messages” into a single standalone query; otherwise `search_query = user_query`. **Retrieval** uses `search_query`; **answer generation** and relevance filtering still use the original `user_query`.

So: **retrieval** uses the reformulated query; **answer** is generated for the original user question.

---

## Full retrieval pipeline (step-by-step)

The pipeline is a **LangGraph** state machine with this flow:

```
START → reformulate_query → retrieve → extract_relevant_chunks → extract_images → extract_relevant_images
  → vlm_summaries → format_context → generate_answer → parse_response
  → filter_images → build_output → END
```

### Step 0: **reformulate_query** (`_node_reformulate_query`)

- **What:** Optionally reformulate the user query for retrieval using the last 3 chat messages (backend-provided).
- **Input:** `state["user_query"]`, `state["chat_history"]` (at most 3 messages, from DB).
- **Output:** `state["search_query"]` = standalone query for vector search, or `user_query` if no history.
- **When skipped:** If `chat_history` is empty, `search_query` is set to `user_query` and no LLM call is made.

### Step 1: **retrieve** (`_node_retrieve`)

- **What:** Vector similarity search in Qdrant. Uses **reformulated** `state["search_query"]` (or `user_query` if no reformulation).
- **How many:** `settings.rag_retrieve_k` documents (default 15).
- **Filter:** If `book_id` is present (e.g. from `/api/books/{book_id}/query`), only chunks with `metadata.book_id == book_id` are considered.
- **Output:** `state["docs"]` = list of up to 15 `Document` objects (LangChain style with `page_content` and `metadata`).

So **15 chunks** are retrieved here.

---

### Step 2: **extract_relevant_chunks** (`_node_extract_relevant_chunks`)

- **What:** LLM-based “reranker”: which of the 15 chunks are actually relevant?
- **Input:** User query + excerpts of each chunk (first 300 chars per chunk), with indices `[0]` … `[14]`.
- **Prompt:** Asks for “chunk indices relevant to answering the user’s question”, **at least `rag_filter_min_chunks` and at most `rag_filter_max_chunks`** (defaults 2 and 10), in relevance order.
- **Output:** Structured output `RelevantChunkIndices`; indices are validated and de-duplicated; `state["docs"]` is replaced by the subset of docs at those indices.
- **Fallback:** On LLM/parsing error, all 15 docs are kept.

So after this step you have **2–10 chunks** (or 15 on fallback).

---

### Step 3: **extract_images** (`_node_extract_images`)

- **What:** Collect all image URLs from the **current** `state["docs"]` (the 2–10 chunks).
- **How:** From each doc’s `metadata["image_urls"]` and `metadata["image_url"]`.
- **Output:** `state["unique_image_urls"]` = deduplicated list of image URLs from those chunks.

No chunk count change; still 2–10 docs.

---

### Step 4: **extract_relevant_images** (`_node_extract_relevant_images`)

- **What:** LLM decides which of `unique_image_urls` are relevant to the user question.
- **Output:** `state["relevant_image_urls"]` = subset of URLs to send to the vision model.
- **Fallback:** If the LLM step fails, all `unique_image_urls` are kept.

Still 2–10 text chunks; only the set of images is filtered.

---

### Step 5: **vlm_summaries** (`_node_vlm_summaries`)

- **What:** For each URL in `relevant_image_urls`, call the vision LLM to summarize the image.
- **Output:** `state["vlm_data_map"]` = `{ url: summary_text }`.

Chunk count unchanged (2–10).

---

### Step 6: **format_context** (`_node_format_context`)

- **What:** Build the string that will be passed to the main LLM as “context”.
- **Contents:**
  1. **Visual block:** For each entry in `vlm_data_map`, add something like  
     `[DIAGRAM i] (IMAGE_URL: url)\nSUMMARY: ...`
  2. **Text block:** For each doc in `state["docs"]` (the 2–10 chunks), add  
     `---\n[SOURCE i] (Page p)\nASSOCIATED_IMAGE_URLS: ...\nCONTENT:\n{doc.page_content}\n---`
- **Output:** `state["context_text"]` = one big string.

So the **number of chunks in the prompt** is exactly the number of docs at this point: **2–10**.

---

### Step 7: **generate_answer** (`_node_generate_answer`)

- **What:** Single LLM call with `context_text` and `user_query`.
- **Output:** `state["response_text"]` = raw model reply (may include CHESS_DATA_JSON blocks).

---

### Step 8: **parse_response** (`_node_parse_response`)

- **What:** Strip CHESS_DATA_JSON blocks, parse FEN/PGN/etc., keep the rest as the answer.
- **Output:** `state["answer"]`, `state["chess_data"]`.

---

### Step 9: **filter_images** (`_node_filter_images`)

- **What:** Decide which of the candidate image URLs are relevant to the **final answer** (and query) for UI display.
- **Output:** `state["filtered_image_urls"]`, `state["filtered_vlm_map"]`.

---

### Step 10: **build_output** (`_node_build_output`)

- **What:** Build the “sources” list from the **current** `state["docs"]` (still the 2–10 chunks).
- **Output:** `state["sources"]` = list of `{"content": doc.page_content, "metadata": doc.metadata}` for each doc.

So the **sources** the user sees are exactly those **2–10 chunks** that made it past the relevance filter and were used in the context.

---

## Summary table

| Step | Node | Chunk count | Notes |
|------|------|-------------|--------|
| 1 | retrieve | **rag_retrieve_k** (default 15) | Vector search with optional `book_id` filter |
| 2 | extract_relevant_chunks | **rag_filter_min–max** (default 2–10) | LLM selects indices; fallback keeps all retrieved |
| 3–10 | rest | same | Same docs through context, answer, and sources |

**Bottom line:**

- **rag_retrieve_k** chunks are retrieved from the vector store per query (default 15).
- **rag_filter_min_chunks** to **rag_filter_max_chunks** of those are used as context and returned as sources (default 2–10).

---

## Where the numbers are defined

- **Retrieval k and filter min/max:**  
  `app/config.py`: `rag_retrieve_k`, `rag_filter_min_chunks`, `rag_filter_max_chunks`. Override via env: `RAG_RETRIEVE_K`, `RAG_FILTER_MIN_CHUNKS`, `RAG_FILTER_MAX_CHUNKS`. Used in `app/services/rag_service.py` in `_node_retrieve` and `_node_extract_relevant_chunks`.
- **Chunk size / overlap at ingest:**  
  `app/services/book_processor.py` → `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)` (not yet in config).

The `vector_store_service.search()` uses `top_k=5` by default; that path is used by other callers (e.g. `book_chatbot` agent). The **book chat UI** goes through `rag_service.query()` and thus uses the configurable pipeline above.

---

## Recommendations (are these ideal?)

- **Retrieve k (default 15):**  
  Over-retrieving then reranking is a good pattern. 15–20 is a solid default; increase to 20–30 if you have long books and broad questions, or decrease to 10 if latency/cost matters and your queries are narrow. Keep `k` ≥ `rag_filter_max_chunks`.

- **Filter min (default 2):**  
  “At least 2” avoids single-chunk answers and gives the model a bit of context. Use 1 if you want to allow a single highly relevant chunk; keep 2 for robustness.

- **Filter max (default 10):**  
  With ~800-char chunks, 10 chunks ≈ 8k chars of book text plus prompts/VLM; that fits comfortably in context. Use 12 if you need more coverage for complex questions; avoid going much higher or you risk context bloat and cost.

- **Tuning:**  
  Start with defaults. If answers feel incomplete, try `RAG_RETRIEVE_K=20` and/or `RAG_FILTER_MAX_CHUNKS=12`. If answers are noisy or slow, try `RAG_RETRIEVE_K=10` and/or `RAG_FILTER_MAX_CHUNKS=6`.
