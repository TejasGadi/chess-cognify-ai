# Streamlit UI Testing Guide

## Overview
This guide provides manual testing instructions for the Streamlit UI. Test all features to ensure the API integration works correctly before building the production React UI.

## Prerequisites

1. **Backend Running**: Ensure FastAPI server is running on `http://localhost:8000`
   ```bash
   cd /Users/tejasgadi/Local_Disk_D/chess-cognify-ai
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Services Running**:
   - PostgreSQL (via Docker Compose)
   - Redis (via Docker Compose)
   - Qdrant (via Docker Compose)
   - Ollama (local, already running)

3. **Start Streamlit**:
   ```bash
   cd /Users/tejasgadi/Local_Disk_D/chess-cognify-ai
   source venv/bin/activate
   streamlit run streamlit_app.py
   ```

## Testing Checklist

### 1. Games Page - Upload Tab ✅

**Test Case 1.1: Upload PGN via Text**
- [ ] Navigate to Games → Upload tab
- [ ] Select "Text" input method
- [ ] Paste a valid PGN string
- [ ] Click "Upload Game"
- **Expected**: Success message with Game ID displayed
- **Expected**: Game ID stored in session state

**Test Case 1.2: Upload PGN via File**
- [ ] Select "File" input method
- [ ] Upload a .pgn or .txt file
- [ ] Verify PGN preview appears
- [ ] Click "Upload Game"
- **Expected**: Success message with Game ID

**Test Case 1.3: Upload with Metadata**
- [ ] Enter valid JSON metadata (e.g., `{"time_control": "600+0"}`)
- [ ] Upload game
- **Expected**: Game uploaded with metadata

**Test Case 1.4: Upload Empty PGN**
- [ ] Leave PGN field empty
- [ ] Click "Upload Game"
- **Expected**: Error message "Please provide PGN data"

**Test Case 1.5: Invalid Metadata JSON**
- [ ] Enter invalid JSON in metadata field
- [ ] Upload game
- **Expected**: Warning message, but game still uploads (metadata ignored)

---

### 2. Games Page - Analyze Tab ✅

**Test Case 2.1: Analyze New PGN**
- [ ] Navigate to Games → Analyze tab
- [ ] Paste PGN in text area
- [ ] Click "Analyze Game"
- **Expected**: Loading spinner appears
- **Expected**: Success message after analysis completes
- **Expected**: Game ID displayed and stored
- **Expected**: Automatically navigates to Review tab (or page refreshes)

**Test Case 2.2: Analyze Existing Game**
- [ ] Enter a valid Game ID
- [ ] Click "Analyze Game"
- **Expected**: Game is analyzed (may take 1-2 minutes)
- **Expected**: Success message

**Test Case 2.3: Analyze Without Input**
- [ ] Leave both fields empty
- [ ] Click "Analyze Game"
- **Expected**: Error message "Please provide either Game ID or PGN"

**Note**: Analysis may take 1-2 minutes depending on game length and Stockfish depth.

---

### 3. Games Page - Review Tab ✅

**Test Case 3.1: Load Complete Review**
- [ ] Navigate to Games → Review tab
- [ ] Enter a Game ID (preferably one that's been analyzed)
- [ ] Click "Load Review" in Overview sub-tab
- **Expected**: JSON display of complete review with:
  - Game details
  - All moves with classifications
  - Summary (accuracy, rating, weaknesses)

**Test Case 3.2: Load Move-by-Move Analysis**
- [ ] Click "Moves" sub-tab
- [ ] Click "Load Moves"
- **Expected**: Dataframe showing all moves with:
  - Ply number
  - Label (Best, Excellent, Good, Inaccuracy, Mistake, Blunder)
  - Centipawn loss
  - Explanations (if available)
  - Accuracy scores

**Test Case 3.3: View Key Mistakes**
- [ ] After loading moves, check "Key Mistakes" section
- **Expected**: Expandable sections for each mistake showing:
  - Move number and label
  - Centipawn loss
  - Explanation (if generated)

**Test Case 3.4: Load Game Summary**
- [ ] Click "Summary" sub-tab
- [ ] Click "Load Summary"
- **Expected**: Metrics displayed:
  - Accuracy percentage
  - Estimated rating
  - Confidence level
- **Expected**: List of weaknesses (if detected)

**Test Case 3.5: Load Engine Analysis**
- [ ] Click "Engine Analysis" sub-tab
- [ ] Click "Load Engine Analysis"
- **Expected**: Dataframe with raw Stockfish data:
  - Ply, FEN, moves
  - Evaluations (before, after, best)

**Test Case 3.6: Review Non-Existent Game**
- [ ] Enter invalid Game ID
- [ ] Try to load review
- **Expected**: Error message (404 or similar)

---

### 4. Games Page - Chat Tab ✅

**Test Case 4.1: Start Chat Session**
- [ ] Navigate to Games → Chat tab
- [ ] Enter a Game ID (preferably analyzed)
- [ ] Type a question (e.g., "What was the best move?")
- [ ] Press Enter or send
- **Expected**: 
  - Loading spinner appears
  - Response appears in chat
  - Session ID created automatically

**Test Case 4.2: Continue Conversation**
- [ ] After first message, ask follow-up question
- **Expected**: 
  - Previous messages visible
  - New response includes context from previous messages

**Test Case 4.3: Chat History Persistence**
- [ ] Send multiple messages
- [ ] Refresh page (F5)
- **Expected**: Chat history is preserved (stored in session state)

**Test Case 4.4: Clear Chat**
- [ ] Click "Clear Chat" button
- **Expected**: All messages cleared
- **Expected**: New session started on next message

**Test Case 4.5: Chat with Non-Existent Game**
- [ ] Enter invalid Game ID
- [ ] Try to send message
- **Expected**: Error message (404)

**Test Case 4.6: Chat with Unanalyzed Game**
- [ ] Enter Game ID of uploaded but not analyzed game
- [ ] Try to chat
- **Expected**: Error or message indicating game needs analysis

---

### 5. Books Page - Upload Tab ✅

**Test Case 5.1: Upload PDF Book**
- [ ] Navigate to Books → Upload tab
- [ ] Select a PDF file (chess book)
- [ ] Optionally enter title and author
- [ ] Click "Upload Book"
- **Expected**: 
  - Loading spinner (processing may take 1-2 minutes)
  - Success message with Book ID
  - Book details displayed (pages, chunks)

**Test Case 5.2: Upload Without File**
- [ ] Click "Upload Book" without selecting file
- **Expected**: Error message "Please select a PDF file"

**Test Case 5.3: Upload with Metadata**
- [ ] Upload PDF with title and author
- **Expected**: Book stored with metadata

**Note**: PDF processing may take 1-2 minutes depending on file size.

---

### 6. Books Page - List Tab ✅

**Test Case 6.1: View Book List**
- [ ] Navigate to Books → List tab
- [ ] Click "Refresh List"
- **Expected**: List of all uploaded books with:
  - Title and author
  - Book ID
  - Filename
  - Total pages
  - Total chunks
  - Created date

**Test Case 6.2: Delete Book**
- [ ] Find a book in the list
- [ ] Click "Delete" button
- **Expected**: 
  - Confirmation or immediate deletion
  - Book removed from list
  - Success message

**Test Case 6.3: Empty Book List**
- [ ] Delete all books
- [ ] Refresh list
- **Expected**: Message "No books uploaded yet"

---

### 7. Books Page - Chat Tab ✅

**Test Case 7.1: Chat with Specific Book**
- [ ] Navigate to Books → Chat tab
- [ ] Select a book from dropdown
- [ ] Type question (e.g., "What are the principles of the Sicilian Defense?")
- [ ] Send message
- **Expected**: 
  - Response based on book content
  - Sources displayed (if available)
  - Session ID created

**Test Case 7.2: Chat Across All Books**
- [ ] Select "All Books" from dropdown
- [ ] Ask a question
- **Expected**: Response searches across all uploaded books

**Test Case 7.3: View Sources**
- [ ] After receiving response, check "Sources" expander
- **Expected**: List of sources with:
  - Filename
  - Section/chunk index

**Test Case 7.4: Continue Conversation**
- [ ] Ask follow-up questions
- **Expected**: Context maintained across messages

**Test Case 7.5: Clear Chat**
- [ ] Click "Clear Chat"
- **Expected**: Messages cleared, new session on next message

---

### 8. Status Page ✅

**Test Case 8.1: Check System Status**
- [ ] Navigate to Status page
- [ ] Click "Refresh Status"
- **Expected**: 
  - Overall status (healthy/degraded/unhealthy)
  - Individual service statuses:
    - PostgreSQL: 🟢 healthy
    - Redis: 🟢 healthy
    - Qdrant: 🟢 healthy
    - Ollama: 🟢 healthy
    - Groq: 🟢 healthy (if API key configured)
    - Stockfish: 🟢 healthy (if binary found)

**Test Case 8.2: Check Metrics**
- [ ] Click "Refresh Metrics"
- **Expected**: 
  - Total games count
  - Analyzed games count
  - Total books count
  - Cache statistics (if available)

**Test Case 8.3: Service Failure Detection**
- [ ] Stop one service (e.g., Redis)
- [ ] Refresh status
- **Expected**: Service shows 🔴 unhealthy with error message

---

### 9. Navigation & Configuration ✅

**Test Case 9.1: Page Navigation**
- [ ] Use sidebar to navigate between pages
- **Expected**: 
  - Active page highlighted
  - Content updates correctly
  - Session state preserved

**Test Case 9.2: API URL Configuration**
- [ ] Change API Base URL in sidebar
- **Expected**: 
  - Success message
  - All subsequent API calls use new URL

**Test Case 9.3: Invalid API URL**
- [ ] Enter invalid API URL
- [ ] Try to make API call
- **Expected**: Network error message

---

## Common Issues & Solutions

### Issue: "Network error" or Connection Refused
**Solution**: 
- Check if FastAPI server is running
- Verify API URL in sidebar is correct
- Check firewall/port settings

### Issue: Analysis Takes Too Long
**Solution**: 
- This is normal for long games
- Check Stockfish is configured correctly
- Monitor server logs for progress

### Issue: Chat Not Working
**Solution**: 
- Verify game has been analyzed
- Check Groq API key is configured
- Check server logs for errors

### Issue: Book Upload Fails
**Solution**: 
- Verify Qdrant is running
- Check Ollama is accessible
- Verify PDF file is valid
- Check file size limits

### Issue: Status Shows Unhealthy Services
**Solution**: 
- Check Docker containers are running
- Verify service URLs in config
- Check service logs

---

## Expected Behavior Summary

### Successful Operations
- ✅ All API calls return 200/201 status
- ✅ Data displays correctly in UI
- ✅ Loading indicators show during operations
- ✅ Success messages appear after operations
- ✅ Error messages are user-friendly

### Error Handling
- ✅ Network errors show clear messages
- ✅ API errors (4xx, 5xx) show detail messages
- ✅ Validation errors show field-specific messages
- ✅ Invalid inputs show warnings

### State Management
- ✅ Selected Game ID persists across tabs
- ✅ Chat sessions persist during page refresh
- ✅ Uploaded files remain in session
- ✅ API URL changes apply immediately

---

## Performance Expectations

- **Game Upload**: < 1 second
- **Game Analysis**: 1-3 minutes (depending on game length)
- **Book Upload**: 1-2 minutes (depending on PDF size)
- **Chat Response**: 2-5 seconds
- **Status Check**: < 1 second
- **Data Loading**: < 1 second

---

## Notes for Production React UI

When building the React UI, consider:
1. **State Management**: Use Redux or Context API for global state
2. **Real-time Updates**: Use WebSockets for analysis progress
3. **Error Handling**: Implement retry logic and better error boundaries
4. **Loading States**: Skeleton loaders instead of spinners
5. **Responsive Design**: Mobile-friendly layouts
6. **Authentication**: Add user authentication
7. **Caching**: Implement client-side caching for frequently accessed data
8. **Optimistic Updates**: Update UI before API confirmation

---

## Testing Completion Checklist

- [ ] All game upload methods tested
- [ ] Game analysis tested with various game lengths
- [ ] All review tabs tested
- [ ] Chat functionality tested
- [ ] Book upload tested
- [ ] Book list and deletion tested
- [ ] Book chat tested (specific and all books)
- [ ] Status page tested
- [ ] Error scenarios tested
- [ ] Navigation tested
- [ ] Configuration tested

**Status**: Ready for React UI development once all tests pass ✅
