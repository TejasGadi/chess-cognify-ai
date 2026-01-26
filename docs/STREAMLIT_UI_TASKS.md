# Streamlit UI Frontend Integration - Tasks

## Overview
Create a Streamlit UI frontend that uses API endpoints (not services directly) for testing all functionality before building the production React UI.

## Task Breakdown

### 1. Setup & Configuration ✅
- [x] Add streamlit to requirements.txt
- [x] Create streamlit app structure
- [x] Configure API base URL
- [x] Set up error handling utilities

### 2. Game Management UI
- [ ] **Game Upload Page**
  - [ ] PGN text input area
  - [ ] File upload option (optional)
  - [ ] Metadata input (optional)
  - [ ] Upload button → POST /api/games/upload
  - [ ] Display uploaded game_id

- [ ] **Game Analysis Page**
  - [ ] Game selection (dropdown or input)
  - [ ] Analyze button → POST /api/games/analyze
  - [ ] Progress indicator during analysis
  - [ ] Display analysis results

- [ ] **Game Review Display**
  - [ ] Game selection
  - [ ] Display game details → GET /api/games/{game_id}
  - [ ] Display complete review → GET /api/games/{game_id}/review
  - [ ] Move-by-move analysis → GET /api/games/{game_id}/moves
  - [ ] Game summary → GET /api/games/{game_id}/summary
  - [ ] Raw engine analysis → GET /api/games/{game_id}/analysis
  - [ ] Visual chess board (optional, using python-chess)

### 3. Game Review Chatbot UI
- [ ] **Chat Interface**
  - [ ] Game selection
  - [ ] Chat message input
  - [ ] Send button → POST /api/games/{game_id}/chat
  - [ ] Display chat history → GET /api/games/{game_id}/chat/history
  - [ ] Session management
  - [ ] Clear chat option

### 4. Book Management UI
- [ ] **Book Upload Page**
  - [ ] PDF file upload → POST /api/books/upload
  - [ ] Title input (optional)
  - [ ] Author input (optional)
  - [ ] Upload progress indicator
  - [ ] Display uploaded book details

- [ ] **Book List Page**
  - [ ] List all books → GET /api/books
  - [ ] Display book metadata (title, author, pages, chunks)
  - [ ] Delete book option → DELETE /api/books/{book_id}
  - [ ] Book selection for chat

### 5. Book Chatbot UI
- [ ] **Book Chat Interface**
  - [ ] Book selection (or "All Books")
  - [ ] Chat message input
  - [ ] Send button → POST /api/books/{book_id}/chat or POST /api/books/chat
  - [ ] Display response with sources
  - [ ] Session management
  - [ ] Clear chat option

### 6. System Status & Metrics UI
- [ ] **Status Dashboard**
  - [ ] System status display → GET /api/status
  - [ ] Service health indicators (PostgreSQL, Redis, Qdrant, Ollama, Groq, Stockfish)
  - [ ] Metrics display → GET /api/metrics
  - [ ] Game statistics
  - [ ] Book statistics
  - [ ] Cache statistics

### 7. Navigation & Layout
- [ ] **Main Navigation**
  - [ ] Sidebar navigation with pages
  - [ ] Page routing
  - [ ] Active page indicator

- [ ] **Layout Structure**
  - [ ] Header with app title
  - [ ] Sidebar for navigation
  - [ ] Main content area
  - [ ] Footer with version info

### 8. Error Handling & User Feedback
- [ ] **Error Display**
  - [ ] API error messages
  - [ ] Validation errors
  - [ ] Network errors
  - [ ] User-friendly error messages

- [ ] **Success Feedback**
  - [ ] Success messages
  - [ ] Loading indicators
  - [ ] Progress bars for long operations

### 9. UI Enhancements
- [ ] **Styling**
  - [ ] Custom CSS (optional)
  - [ ] Color scheme
  - [ ] Responsive layout

- [ ] **Data Visualization**
  - [ ] Move accuracy chart
  - [ ] Game phase breakdown
  - [ ] Mistake distribution
  - [ ] Rating estimation display

## API Endpoints to Integrate

### Games
- `POST /api/games/upload` - Upload PGN
- `POST /api/games/analyze` - Analyze game
- `GET /api/games/{game_id}` - Get game details
- `GET /api/games/{game_id}/review` - Get complete review
- `GET /api/games/{game_id}/moves` - Get move-by-move analysis
- `GET /api/games/{game_id}/summary` - Get game summary
- `GET /api/games/{game_id}/analysis` - Get raw engine analysis

### Chat
- `POST /api/games/{game_id}/chat` - Chat with game review
- `GET /api/games/{game_id}/chat/history` - Get chat history

### Books
- `POST /api/books/upload` - Upload book PDF
- `GET /api/books` - List all books
- `GET /api/books/{book_id}` - Get book details
- `DELETE /api/books/{book_id}` - Delete book
- `POST /api/books/{book_id}/chat` - Chat with specific book
- `POST /api/books/chat` - Chat across all books

### Status
- `GET /api/status` - System status
- `GET /api/metrics` - System metrics

## Implementation Notes

1. **API Client**: Use `httpx` or `requests` for API calls
2. **State Management**: Use Streamlit session state for:
   - Selected game_id
   - Selected book_id
   - Chat sessions
   - Uploaded files
3. **Error Handling**: Wrap all API calls in try-except blocks
4. **Loading States**: Use `st.spinner()` for async operations
5. **Data Display**: Use Streamlit's built-in components (tables, JSON, markdown)

## Testing Guide

See `STREAMLIT_TESTING_GUIDE.md` for manual testing instructions.
