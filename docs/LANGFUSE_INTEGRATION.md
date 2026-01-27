# Langfuse Integration Guide

## Overview

Langfuse has been integrated into the Chess Cognify AI project for observability and tracing of LLM applications. It automatically captures detailed traces of LangChain/LangGraph executions, LLM calls, tool usage, and retrievers.

**Reference:** [Langfuse LangChain Integration](https://langfuse.com/integrations/frameworks/langchain)

---

## Installation

```bash
pip install -r requirements.txt
```

This will install `langfuse>=3.0.0`.

---

## Configuration

### 1. Get Langfuse API Keys

1. Sign up for a free account at [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Create a new project
3. Navigate to Settings → API Keys
4. Copy your **Public Key** and **Secret Key**

### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Langfuse Observability
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
# LANGFUSE_BASE_URL=https://us.cloud.langfuse.com  # For US region
LANGFUSE_ENABLED=true
```

### 3. Disable Langfuse (Optional)

If you want to disable tracing without removing the code:

```bash
LANGFUSE_ENABLED=false
```

---

## What Gets Traced

### 1. LangGraph Workflow
- **Location:** `app/agents/supervisor_agent.py`
- **Traces:** Complete workflow execution
  - PGN validation
  - Engine analysis
  - Move classification
  - Explanation generation
  - Accuracy calculation
  - Weakness detection
  - Final review

### 2. Explanation Agent
- **Location:** `app/agents/explanation_agent.py`
- **Traces:** LLM calls for move explanations
  - Input: Position representation, move context
  - Output: Structured explanation
  - Model: OpenAI GPT-4o

### 3. Weakness Detection Agent
- **Location:** `app/agents/weakness_detection_agent.py`
- **Traces:** LLM calls for weakness detection
  - Input: Game phase breakdown, mistakes
  - Output: Weakness categories
  - Model: OpenAI GPT-4o

### 4. Game Review Chatbot
- **Location:** `app/agents/game_review_chatbot.py`
- **Traces:** LLM calls for game review Q&A
  - Input: User query, game context
  - Output: Chatbot response
  - Model: OpenAI GPT-4o

### 5. Book Chatbot
- **Location:** `app/agents/book_chatbot.py`
- **Traces:** LLM calls for book Q&A (RAG)
  - Input: User query, retrieved chunks
  - Output: Chatbot response with sources
  - Model: OpenAI GPT-4o

---

## Viewing Traces

1. **Start the FastAPI server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Run a game analysis** (via Streamlit UI or API)

3. **View traces in Langfuse:**
   - Navigate to [https://cloud.langfuse.com](https://cloud.langfuse.com)
   - Go to **Traces** tab
   - You'll see:
     - Complete workflow traces
     - Individual LLM calls
     - Input/output data
     - Latency metrics
     - Token usage and costs
     - Error traces (if any)

---

## Trace Structure

### Workflow Trace
```
TRACE: Game Review Workflow
├── SPAN: validate_pgn
├── SPAN: analyze_engine
│   ├── GENERATION: Stockfish analysis (multiple moves)
├── SPAN: classify_moves
├── SPAN: generate_explanations
│   ├── GENERATION: Explanation for move 1
│   ├── GENERATION: Explanation for move 2
│   └── ... (parallel generations)
├── SPAN: calculate_accuracy_rating
├── SPAN: detect_weaknesses
│   └── GENERATION: Weakness detection LLM call
└── SPAN: finalize_review
```

### Individual LLM Trace
```
GENERATION: OpenAI GPT-4o
├── Input: Prompt with position representation
├── Output: Structured explanation
├── Tokens: Input/Output counts
├── Latency: Request duration
└── Cost: Calculated cost
```

---

## Features

### Automatic Tracing
- All LLM calls are automatically traced
- No code changes needed in agent logic
- Graceful degradation if Langfuse is disabled

### Detailed Metrics
- **Latency:** Request duration for each LLM call
- **Tokens:** Input/output token counts
- **Cost:** Calculated cost based on model pricing
- **Errors:** Full error traces with stack traces

### Workflow Visualization
- See complete LangGraph workflow execution
- Understand data flow between nodes
- Identify bottlenecks and slow operations

### Debugging
- View exact inputs sent to LLM
- See raw outputs before processing
- Track tool usage and retrievals
- Identify failed or slow operations

---

## Implementation Details

### Handler Initialization
- **File:** `app/utils/langfuse_handler.py`
- **Function:** `get_langfuse_handler()`
- **Pattern:** Singleton pattern (one handler instance)
- **Initialization:** On FastAPI startup (`app/main.py`)

### Integration Pattern
All agents use the same pattern:

```python
from app.utils.langfuse_handler import get_langfuse_handler

langfuse_handler = get_langfuse_handler()
config = {}
if langfuse_handler:
    config["callbacks"] = [langfuse_handler]

result = await chain.ainvoke(input, config=config)
```

### Graceful Degradation
- If Langfuse is disabled or keys are missing, tracing is skipped
- Application continues to work normally
- No errors or warnings (only debug logs)

---

## Troubleshooting

### Traces Not Appearing

1. **Check environment variables:**
   ```bash
   echo $LANGFUSE_SECRET_KEY
   echo $LANGFUSE_PUBLIC_KEY
   ```

2. **Verify Langfuse is enabled:**
   ```bash
   echo $LANGFUSE_ENABLED
   ```

3. **Check logs for initialization:**
   ```
   [LANGFUSE] Initialized Langfuse client
   ```

4. **Verify API keys are correct:**
   - Keys should start with `sk-lf-` and `pk-lf-`
   - Check in Langfuse dashboard → Settings → API Keys

### High Latency

- Langfuse tracing is asynchronous and shouldn't impact performance
- If you notice slowdowns, check network connectivity to Langfuse servers
- Consider using `LANGFUSE_ENABLED=false` for local development

### Missing Traces

- Ensure callbacks are passed correctly to `ainvoke()` calls
- Check that `get_langfuse_handler()` returns a handler (not None)
- Verify Langfuse client initialization succeeded

---

## Best Practices

1. **Development:** Keep `LANGFUSE_ENABLED=true` to catch issues early
2. **Production:** Always enable Langfuse for monitoring
3. **Testing:** Can disable Langfuse for faster test runs
4. **Debugging:** Use Langfuse dashboard to debug failed LLM calls
5. **Optimization:** Use trace data to identify slow operations

---

## Additional Resources

- [Langfuse Documentation](https://langfuse.com/docs)
- [LangChain Integration Guide](https://langfuse.com/integrations/frameworks/langchain)
- [LangGraph Tracing](https://langfuse.com/integrations/frameworks/langchain#langgraph)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)

---

## Summary

✅ **Integrated:** Langfuse callback handler in all LLM agents  
✅ **Traced:** LangGraph workflow and all LLM calls  
✅ **Configurable:** Can be enabled/disabled via environment variable  
✅ **Graceful:** Degrades gracefully if disabled or misconfigured  
✅ **Production-Ready:** Suitable for production monitoring
