"""
Streamlit UI for AI Chess Game Review Coach.

This UI uses API endpoints (not services directly) for all operations.
"""
import streamlit as st
import httpx
import json
import chess
import chess.svg
import chess.pgn
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from io import StringIO
import base64

logger = logging.getLogger(__name__)

# Page configuration MUST be first
st.set_page_config(
    page_title="Chess Cognify AI",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configuration (after set_page_config)
if "API_BASE_URL" not in st.session_state:
    try:
        # Try to get from secrets, fallback to default
        st.session_state.API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:8000")
    except:
        # If secrets not configured, use default
        st.session_state.API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "selected_game_id" not in st.session_state:
    st.session_state.selected_game_id = None
if "selected_book_id" not in st.session_state:
    st.session_state.selected_book_id = None
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}
if "book_chat_sessions" not in st.session_state:
    st.session_state.book_chat_sessions = {}


def api_request(
    method: str, endpoint: str, data: Optional[Dict] = None, files: Optional[Dict] = None, timeout: float = 300.0
) -> Optional[Dict]:
    """Make API request and return response."""
    url = f"{st.session_state.API_BASE_URL}{endpoint}"
    
    try:
        # Use longer timeout for analysis endpoint
        if "/analyze" in endpoint:
            timeout = 300.0  # 5 minutes for analysis
        
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                response = client.get(url)
            elif method == "POST":
                if files:
                    response = client.post(url, data=data, files=files)
                else:
                    response = client.post(url, json=data)
            elif method == "DELETE":
                response = client.delete(url)
            else:
                st.error(f"Unsupported method: {method}")
                return None

            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            elif response.status_code == 204:
                # DELETE operations return 204 No Content
                return {}
            else:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("detail", error_msg)
                except:
                    pass
                st.error(f"API Error ({response.status_code}): {error_msg}")
                return None
    except httpx.TimeoutException:
        st.error(f"Request timed out. The analysis is taking longer than expected. Please check the backend logs.")
        return None
    except httpx.RequestError as e:
        st.error(f"Network error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None


def render_chess_board(board: chess.Board, last_move: Optional[chess.Move] = None, size: int = 400) -> str:
    """Render chess board as SVG HTML."""
    svg = chess.svg.board(board=board, lastmove=last_move, size=size)
    return f'<div style="display: flex; justify-content: center;">{svg}</div>'


def pgn_to_board(pgn: str, move_number: Optional[int] = None) -> Optional[chess.Board]:
    """Convert PGN to board at specific move number."""
    try:
        game = chess.pgn.read_game(StringIO(pgn))
        if game is None:
            return None
        board = game.board()
        moves = list(game.mainline_moves())
        if move_number is None:
            move_number = len(moves)
        for move in moves[:move_number]:
            board.push(move)
        return board
    except Exception as e:
        st.error(f"Error parsing PGN: {str(e)}")
        return None


def page_games():
    """Game management and review page."""
    st.header("♟️ Game Management & Review")

    tab1, tab2, tab3 = st.tabs(["Analyze Game", "Review", "Chat"])

    with tab1:
        st.subheader("Upload & Analyze Game")
        
        # Input method selection
        input_method = st.radio("Input Method", ["PGN Text", "Visual Board", "Game ID"], horizontal=True, key="input_method")
        
        pgn_for_analysis = None
        metadata = None
        
        if input_method == "PGN Text":
            # Text input
            pgn_text = st.text_area("PGN String", height=200, placeholder="Paste PGN here...")
            if pgn_text.strip():
                pgn_for_analysis = pgn_text.strip()
            
            # Optional metadata
            metadata_input = st.text_input("Metadata (JSON, optional)", placeholder='{"time_control": "600+0"}', key="metadata_text")
            if metadata_input:
                try:
                    metadata = json.loads(metadata_input)
                except:
                    st.warning("Invalid JSON, ignoring metadata")
            
            # File upload option
            st.markdown("---")
            st.markdown("**Or upload PGN file:**")
            uploaded_file = st.file_uploader("Upload PGN file", type=["pgn", "txt"], key="file_upload")
            if uploaded_file:
                pgn_for_analysis = uploaded_file.read().decode("utf-8")
                st.text_area("PGN Preview", pgn_for_analysis, height=150, disabled=True)
        
        elif input_method == "Visual Board":
            # Visual board input
            st.markdown("### Interactive Chess Board")
            st.info("Enter moves in algebraic notation (e.g., e4, Nf3) or paste a PGN below")
            
            # Initialize board state
            if "board_moves" not in st.session_state:
                st.session_state.board_moves = []
                st.session_state.current_board = chess.Board()
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Display board
                board_html = render_chess_board(st.session_state.current_board)
                st.markdown(board_html, unsafe_allow_html=True)
            
            with col2:
                st.markdown("### Move Input")
                move_input = st.text_input("Enter move (SAN)", placeholder="e.g., e4, Nf3", key="move_input")
                
                if st.button("Add Move", key="add_move"):
                    try:
                        move = st.session_state.current_board.parse_san(move_input)
                        if move in st.session_state.current_board.legal_moves:
                            st.session_state.current_board.push(move)
                            st.session_state.board_moves.append(move_input)
                            st.success(f"Move {len(st.session_state.board_moves)}: {move_input}")
                            st.rerun()
                        else:
                            st.error("Illegal move!")
                    except Exception as e:
                        st.error(f"Invalid move: {str(e)}")
                
                if st.button("Undo Last Move", key="undo_move"):
                    if st.session_state.board_moves:
                        st.session_state.current_board.pop()
                        st.session_state.board_moves.pop()
                        st.rerun()
                
                if st.button("Clear Board", key="clear_board"):
                    st.session_state.board_moves = []
                    st.session_state.current_board = chess.Board()
                    st.rerun()
                
                st.markdown("### Move List")
                if st.session_state.board_moves:
                    moves_text = " ".join([f"{i+1}. {move}" if i % 2 == 0 else f"{move}" 
                                          for i, move in enumerate(st.session_state.board_moves)])
                    st.text_area("PGN Moves", moves_text, height=100, disabled=True)
                    
                    # Generate PGN from moves
                    try:
                        temp_board = chess.Board()
                        pgn_moves = []
                        for i, move_str in enumerate(st.session_state.board_moves):
                            move = temp_board.parse_san(move_str)
                            temp_board.push(move)
                            # Format for PGN
                            if i % 2 == 0:
                                pgn_moves.append(f"{temp_board.fullmove_number - 1}. {move_str}")
                            else:
                                pgn_moves.append(move_str)
                        pgn_for_analysis = " ".join(pgn_moves)
                    except Exception as e:
                        st.warning(f"Could not generate PGN: {str(e)}")
                        pgn_for_analysis = None
                else:
                    st.info("No moves entered yet")
            
            # Also allow PGN paste as alternative
            st.markdown("---")
            pgn_override = st.text_area("Or paste full PGN here", height=100, 
                                        placeholder="Paste complete PGN to override board moves...", key="pgn_override")
            if pgn_override.strip():
                pgn_for_analysis = pgn_override.strip()
        
        else:  # Game ID
            game_id_input = st.text_input("Enter Game ID", value=st.session_state.selected_game_id or "", key="game_id_input")
            
            if game_id_input:
                # Load game info
                game = api_request("GET", f"/api/games/{game_id_input}")
                if game:
                    st.info(f"Game found: {game.get('game_id', 'N/A')}")
                    pgn_for_analysis = game["pgn"]
                    metadata = game.get("metadata")
                else:
                    st.error("Game not found. Please check the Game ID.")

        # Analyze button
        st.markdown("---")
        
        # Initialize analysis state
        if "analysis_in_progress" not in st.session_state:
            st.session_state.analysis_in_progress = False
        
        analyze_button = st.button("🚀 Analyze Game", type="primary", use_container_width=True, disabled=st.session_state.analysis_in_progress)
        
        if analyze_button or st.session_state.analysis_in_progress:
            if not pgn_for_analysis:
                st.error("❌ Please provide PGN data or select a Game ID")
                st.session_state.analysis_in_progress = False
            else:
                # Set analysis state
                st.session_state.analysis_in_progress = True
                
                # Show loading immediately
                with st.spinner("🔄 Analyzing game... This may take 1-2 minutes. Please wait and don't close this page."):
                    try:
                        # Make API request with longer timeout for analysis
                        result = api_request("POST", "/api/games/analyze", {
                            "pgn": pgn_for_analysis,
                            "metadata": metadata
                        }, timeout=300.0)
                        
                        # api_request returns None on error, and errors are already displayed
                        if result is None:
                            # Error was already shown by api_request
                            st.session_state.analysis_in_progress = False
                            st.stop()
                        
                        # Validate that analysis actually succeeded
                        moves_count = len(result.get("moves", []))
                        summary = result.get("summary", {})
                        accuracy = summary.get("accuracy", 0)
                        
                        # Check if analysis actually worked - 0 moves means failure
                        if moves_count == 0:
                            st.error("❌ Analysis failed - no moves were analyzed")
                            st.warning("⚠️ This usually means:")
                            st.write("1. Stockfish engine is not found or not accessible")
                            st.write("2. Stockfish path is incorrect in configuration")
                            st.write("3. Analysis workflow encountered an error")
                            st.info("💡 **Fix:**")
                            st.code("brew install stockfish  # macOS\n# Or set STOCKFISH_PATH=/path/to/stockfish in .env file", language="bash")
                            st.write("Then restart your FastAPI server.")
                            st.session_state.analysis_in_progress = False
                        elif accuracy == 0 and moves_count > 0:
                            # This might be a valid game with 0% accuracy (very bad game)
                            st.warning("⚠️ Analysis completed but accuracy is 0%. This might indicate an issue.")
                            st.success("✅ Analysis complete!")
                            st.info(f"**Game ID**: `{result.get('game_id', 'N/A')}`")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Accuracy", f"{accuracy}%")
                            with col2:
                                st.metric("Estimated Rating", summary.get('estimated_rating', 400))
                            with col3:
                                st.metric("Moves Analyzed", moves_count)
                            st.session_state.analysis_in_progress = False
                        else:
                            # Success case
                            st.success("✅ Analysis complete!")
                            st.info(f"**Game ID**: `{result.get('game_id', 'N/A')}`")
                            
                            # Show summary metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Accuracy", f"{accuracy}%")
                            with col2:
                                st.metric("Estimated Rating", summary.get('estimated_rating', 400))
                            with col3:
                                st.metric("Moves Analyzed", moves_count)
                            
                            # Show weaknesses if available
                            if summary.get("weaknesses"):
                                with st.expander("📊 Detected Weaknesses"):
                                    for weakness in summary["weaknesses"]:
                                        st.write(f"- {weakness}")
                            
                            st.session_state.selected_game_id = result.get("game_id")
                            
                            # Clear board state if used
                            if "board_moves" in st.session_state:
                                del st.session_state.board_moves
                                del st.session_state.current_board
                            
                            st.info("💡 Switch to the 'Review' tab to see detailed move-by-move analysis")
                            st.session_state.analysis_in_progress = False
                            
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")
                        st.info("💡 Check your backend server logs for more details. Make sure Stockfish is installed and accessible.")
                        st.session_state.analysis_in_progress = False

    with tab2:
        st.subheader("Game Review")
        
        game_id = st.text_input("Game ID", value=st.session_state.selected_game_id or "", key="review_game_id")
        
        if game_id:
            review_tabs = st.tabs(["Overview", "Moves", "Summary", "Engine Analysis"])

            with review_tabs[0]:
                # Complete review
                if st.button("Load Review"):
                    with st.spinner("Loading review..."):
                        review = api_request("GET", f"/api/games/{game_id}/review")
                        if review:
                            st.json(review)

            with review_tabs[1]:
                # Move-by-move analysis with board
                # Initialize session state keys
                if f"review_moves_{game_id}" not in st.session_state:
                    st.session_state[f"review_moves_{game_id}"] = None
                if f"review_game_data_{game_id}" not in st.session_state:
                    st.session_state[f"review_game_data_{game_id}"] = None
                if "review_move_number" not in st.session_state:
                    st.session_state.review_move_number = 0
                
                # Load button
                if st.button("Load Moves", key=f"load_moves_{game_id}"):
                    with st.spinner("Loading moves..."):
                        moves = api_request("GET", f"/api/games/{game_id}/moves")
                        game_data = api_request("GET", f"/api/games/{game_id}")
                        
                        if moves and game_data:
                            st.session_state[f"review_moves_{game_id}"] = moves
                            st.session_state[f"review_game_data_{game_id}"] = game_data
                            st.session_state.review_move_number = 0
                            st.rerun()
                
                # Display board if data is loaded (persists across reruns)
                moves = st.session_state[f"review_moves_{game_id}"]
                game_data = st.session_state[f"review_game_data_{game_id}"]
                
                if moves and game_data:
                    pgn = game_data.get("pgn", "")
                    board = pgn_to_board(pgn, st.session_state.review_move_number)
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("### Chess Board")
                        if board:
                            # Get last move if available
                            last_move = None
                            if st.session_state.review_move_number > 0:
                                try:
                                    game = chess.pgn.read_game(StringIO(pgn))
                                    if game:
                                        moves_list = list(game.mainline_moves())
                                        if st.session_state.review_move_number > 0 and st.session_state.review_move_number <= len(moves_list):
                                            last_move = moves_list[st.session_state.review_move_number - 1]
                                except:
                                    pass
                            
                            board_html = render_chess_board(board, last_move=last_move, size=450)
                            st.markdown(board_html, unsafe_allow_html=True)
                            
                            # Navigation controls
                            nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
                            with nav_col1:
                                if st.button("⏮️ Start", key="nav_start"):
                                    st.session_state.review_move_number = 0
                                    st.rerun()
                            with nav_col2:
                                if st.button("⏪ Previous", key="nav_prev"):
                                    if st.session_state.review_move_number > 0:
                                        st.session_state.review_move_number -= 1
                                        st.rerun()
                            with nav_col3:
                                if st.button("⏩ Next", key="nav_next"):
                                    max_moves = len(moves)
                                    if st.session_state.review_move_number < max_moves:
                                        st.session_state.review_move_number += 1
                                        st.rerun()
                            with nav_col4:
                                if st.button("⏭️ End", key="nav_end"):
                                    st.session_state.review_move_number = len(moves)
                                    st.rerun()
                            
                            # Show position caption
                            if st.session_state.review_move_number == 0:
                                st.caption("Initial Position")
                            else:
                                st.caption(f"After Move {st.session_state.review_move_number} of {len(moves)}")
                    
                    with col2:
                        st.markdown("### Move Analysis")
                        
                        # Current move info - only show when there are moves on the board
                        # When review_move_number = 0, board shows initial position, so no move analysis
                        # When review_move_number = 1, board shows after move 1, so show move 1 (index 0)
                        if st.session_state.review_move_number > 0 and st.session_state.review_move_number <= len(moves):
                            # Move index is review_move_number - 1 (move 1 is at index 0)
                            move_index = st.session_state.review_move_number - 1
                            current_move = moves[move_index]
                            
                            # Move header
                            st.markdown(f"#### Move {current_move.get('ply', 'N/A')}")
                            
                            # Move quality and evaluation
                            metric_col1, metric_col2 = st.columns(2)
                            with metric_col1:
                                label = current_move.get('label', 'N/A')
                                label_emoji = {
                                    'Best': '✅',
                                    'Good': '👍',
                                    'Inaccuracy': '⚠️',
                                    'Mistake': '❌',
                                    'Blunder': '💥'
                                }.get(label, '')
                                st.metric("Quality", f"{label_emoji} {label}")
                            
                            with metric_col2:
                                eval_after = current_move.get('eval_after', 'N/A')
                                st.metric("Evaluation", eval_after)
                            
                            st.markdown("---")
                            
                            # Move played
                            move_san = current_move.get('move_san', 'N/A')
                            st.markdown(f"**Move Played**: `{move_san}`")
                            
                            # Top 5 Engine Moves
                            top_moves = current_move.get('top_moves', [])
                            if top_moves:
                                st.markdown("**Top Engine Moves in this position:**")
                                for i, top_move in enumerate(top_moves[:5], 1):
                                    move_san_top = top_move.get('move_san', top_move.get('move', 'N/A'))
                                    eval_str = top_move.get('eval_str', 'N/A')
                                    
                                    # Highlight if this is the played move
                                    is_played = move_san_top == move_san
                                    prefix = "👉 " if is_played else f"{i}. "
                                    color = "🟢" if is_played else ""
                                    
                                    st.markdown(f"{color} {prefix}`{move_san_top}` - **{eval_str}**")
                            
                            st.markdown("---")
                            
                            # AI Comment on the move (always shown)
                            explanation = current_move.get('explanation')
                            if explanation:
                                st.markdown("**AI Comment:**")
                                st.info(explanation)
                            else:
                                st.warning("⚠️ Analysis comment not available for this move")
                        else:
                            # Show empty state when at initial position
                            if st.session_state.review_move_number == 0:
                                st.info("👆 Click 'Next' to see the first move analysis")
                            else:
                                st.warning("⚠️ No move data available for this position")
                        
                        st.markdown("---")
                        st.markdown("### All Moves")
                        st.dataframe(moves, use_container_width=True, height=400)
                    
                    # Show mistakes
                    mistakes = [m for m in moves if m.get("label") in ["Inaccuracy", "Mistake", "Blunder"]]
                    if mistakes:
                        st.markdown("---")
                        st.subheader("Key Mistakes")
                        for move in mistakes:
                            with st.expander(f"Move {move['ply']}: {move['label']} - {move.get('move_san', 'N/A')}"):
                                st.write(f"**Centipawn Loss**: {move.get('centipawn_loss', 'N/A')}")
                                if move.get("explanation"):
                                    st.write(f"**Explanation**: {move['explanation']}")
                elif moves is None and game_data is None:
                    st.info("👆 Click 'Load Moves' to load the game analysis")

            with review_tabs[2]:
                # Game summary
                if st.button("Load Summary"):
                    with st.spinner("Loading summary..."):
                        summary = api_request("GET", f"/api/games/{game_id}/summary")
                        if summary:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Accuracy", f"{summary.get('accuracy', 'N/A')}%")
                            with col2:
                                st.metric("Estimated Rating", summary.get("estimated_rating", "N/A"))
                            with col3:
                                st.metric("Confidence", summary.get("rating_confidence", "N/A"))
                            
                            if summary.get("weaknesses"):
                                st.subheader("Weaknesses")
                                for weakness in summary["weaknesses"]:
                                    st.write(f"- {weakness}")

            with review_tabs[3]:
                # Raw engine analysis
                if st.button("Load Engine Analysis"):
                    with st.spinner("Loading engine analysis..."):
                        analysis = api_request("GET", f"/api/games/{game_id}/analysis")
                        if analysis:
                            st.dataframe(analysis, use_container_width=True)

    with tab3:
        st.subheader("Game Review Chatbot")
        
        game_id = st.text_input("Game ID", value=st.session_state.selected_game_id or "", key="chat_game_id")
        
        if game_id:
            # Initialize chat session
            if game_id not in st.session_state.chat_sessions:
                st.session_state.chat_sessions[game_id] = {
                    "session_id": None,
                    "messages": []
                }
            
            session = st.session_state.chat_sessions[game_id]
            
            # Display chat history
            st.subheader("Chat History")
            chat_container = st.container()
            with chat_container:
                if session["messages"]:
                    for msg in session["messages"]:
                        role = msg["role"]
                        content = msg["content"]
                        if role == "user":
                            with st.chat_message("user"):
                                st.write(content)
                        else:
                            with st.chat_message("assistant"):
                                st.write(content)
                else:
                    st.info("No messages yet. Start a conversation!")
            
            # Chat input
            user_message = st.chat_input("Ask about the game...")
            if user_message:
                with st.spinner("Thinking..."):
                    result = api_request("POST", f"/api/games/{game_id}/chat", {
                        "message": user_message,
                        "session_id": session["session_id"]
                    })
                    if result:
                        session["session_id"] = result["session_id"]
                        session["messages"].append({"role": "user", "content": user_message})
                        session["messages"].append({"role": "assistant", "content": result["response"]})
                        st.rerun()
            
            if st.button("Clear Chat"):
                session["messages"] = []
                session["session_id"] = None
                st.rerun()


def page_books():
    """Book management and chatbot page."""
    st.header("📚 Book Management & Chatbot")

    tab1, tab2, tab3 = st.tabs(["Upload", "List", "Chat"])

    with tab1:
        st.subheader("Upload Chess Book PDF")
        
        uploaded_file = st.file_uploader("Upload PDF file", type=["pdf"])
        title = st.text_input("Book Title (optional)")
        author = st.text_input("Book Author (optional)")

        if st.button("Upload Book", type="primary"):
            if not uploaded_file:
                st.error("Please select a PDF file")
            else:
                with st.spinner("Uploading and processing book (this may take a while)..."):
                    # Read file content once
                    file_content = uploaded_file.read()
                    # Reset file pointer for httpx
                    uploaded_file.seek(0)
                    
                    # Prepare multipart form data
                    files = {"file": (uploaded_file.name, file_content, "application/pdf")}
                    data = {}
                    if title:
                        data["title"] = title
                    if author:
                        data["author"] = author
                    
                    result = api_request("POST", "/api/books/upload", data=data, files=files)
                    if result:
                        st.success("Book uploaded successfully!")
                        st.info(f"Book ID: `{result['book_id']}`")
                        st.json(result)

    with tab2:
        st.subheader("Book List")
        
        # Load books on page load or refresh
        if "books_list" not in st.session_state or st.button("Refresh List"):
            with st.spinner("Loading books..."):
                result = api_request("GET", "/api/books")
                if result:
                    st.session_state.books_list = result.get("books", [])
                else:
                    st.session_state.books_list = []
        
        books = st.session_state.get("books_list", [])
        if books:
            for book in books:
                with st.expander(f"📖 {book.get('title', 'Untitled')} - {book.get('author', 'Unknown')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Book ID**: `{book['book_id']}`")
                        st.write(f"**Filename**: {book.get('filename', 'N/A')}")
                        st.write(f"**Pages**: {book.get('total_pages', 'N/A')}")
                    with col2:
                        st.write(f"**Chunks**: {book.get('total_chunks', 'N/A')}")
                        st.write(f"**Created**: {book.get('created_at', 'N/A')}")
                    
                    if st.button(f"Delete", key=f"delete_{book['book_id']}"):
                        with st.spinner("Deleting book..."):
                            delete_result = api_request("DELETE", f"/api/books/{book['book_id']}")
                            # DELETE returns 204 (empty response), which is success
                            if delete_result is not None:  # {} for 204, None for error
                                st.success("Book deleted!")
                                # Clear cached lists
                                if "books_list" in st.session_state:
                                    del st.session_state.books_list
                                if "books_loaded" in st.session_state:
                                    del st.session_state.books_loaded
                                st.rerun()
        else:
            st.info("No books uploaded yet. Upload a book in the Upload tab.")

    with tab3:
        st.subheader("Book Chatbot")
        
        # Get books list (use cached if available, or load)
        if "book_options" not in st.session_state or st.button("Refresh Books", key="refresh_books_chat"):
            books_result = api_request("GET", "/api/books")
            book_options = ["All Books"]
            book_map = {}
            
            if books_result and books_result.get("books"):
                for book in books_result["books"]:
                    book_title = f"{book.get('title', 'Untitled')} ({book['book_id'][:8]}...)"
                    book_options.append(book_title)
                    book_map[book_title] = book["book_id"]
            
            st.session_state.book_options = book_options
            st.session_state.book_map = book_map
        
        # Use cached books
        book_options = st.session_state.get("book_options", ["All Books"])
        book_map = st.session_state.get("book_map", {})
        
        selected_book = st.selectbox("Select Book", book_options)
        book_id = None if selected_book == "All Books" else book_map.get(selected_book)
        
        # Initialize chat session
        session_key = book_id or "all_books"
        if session_key not in st.session_state.book_chat_sessions:
            st.session_state.book_chat_sessions[session_key] = {
                "session_id": None,
                "messages": []
            }
        
        session = st.session_state.book_chat_sessions[session_key]
        
        # Display chat history
        st.subheader("Chat History")
        chat_container = st.container()
        with chat_container:
            if session["messages"]:
                for msg in session["messages"]:
                    role = msg["role"]
                    content = msg["content"]
                    if role == "user":
                        with st.chat_message("user"):
                            st.write(content)
                    else:
                        with st.chat_message("assistant"):
                            st.write(content)
                            # Show sources if available
                            if "sources" in msg and msg["sources"]:
                                with st.expander("Sources"):
                                    for source in msg["sources"]:
                                        st.write(f"- {source.get('filename', 'Unknown')} (Section {source.get('chunk_index', 'N/A')})")
            else:
                st.info("No messages yet. Ask a question about chess!")
        
        # Chat input
        user_message = st.chat_input("Ask about chess...")
        if user_message:
            with st.spinner("Thinking..."):
                if book_id:
                    result = api_request("POST", f"/api/books/{book_id}/chat", {
                        "message": user_message,
                        "session_id": session["session_id"]
                    })
                else:
                    result = api_request("POST", "/api/books/chat", {
                        "message": user_message,
                        "session_id": session["session_id"]
                    })
                
                if result:
                    session["session_id"] = result["session_id"]
                    session["messages"].append({"role": "user", "content": user_message})
                    session["messages"].append({
                        "role": "assistant",
                        "content": result["response"],
                        "sources": result.get("sources", [])
                    })
                    st.rerun()
        
        if st.button("Clear Chat"):
            session["messages"] = []
            session["session_id"] = None
            st.rerun()


def page_status():
    """System status and metrics page."""
    st.header("📊 System Status & Metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("System Status")
        if st.button("Refresh Status"):
            with st.spinner("Checking system status..."):
                status = api_request("GET", "/api/status")
                if status:
                    overall_status = status.get("status", "unknown")
                    st.metric("Overall Status", overall_status.upper())
                    
                    services = status.get("services", {})
                    for service_name, service_info in services.items():
                        service_status = service_info.get("status", "unknown")
                        color = "🟢" if service_status == "healthy" else "🟡" if service_status == "degraded" else "🔴"
                        st.write(f"{color} **{service_name.upper()}**: {service_status}")
                        if service_info.get("message"):
                            st.caption(service_info["message"])

    with col2:
        st.subheader("System Metrics")
        if st.button("Refresh Metrics"):
            with st.spinner("Loading metrics..."):
                metrics = api_request("GET", "/api/metrics")
                if metrics:
                    games = metrics.get("games", {})
                    books = metrics.get("books", {})
                    cache = metrics.get("cache", {})
                    
                    st.metric("Total Games", games.get("total", 0))
                    st.metric("Analyzed Games", games.get("analyzed", 0))
                    st.metric("Total Books", books.get("total", 0))
                    
                    if cache.get("status") == "available":
                        st.write("**Cache Status**: Available")
                        st.write(f"**Memory**: {cache.get('used_memory', 'N/A')}")
                        st.write(f"**Clients**: {cache.get('connected_clients', 'N/A')}")


def main():
    """Main application."""
    # Sidebar navigation
    st.sidebar.title("♟️ Chess Cognify AI")
    st.sidebar.markdown("---")
     
    page = st.sidebar.radio(
        "Navigation",
        ["Games", "Books", "Status"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Configuration")
    api_url = st.sidebar.text_input("API Base URL", value=st.session_state.API_BASE_URL)
    if api_url != st.session_state.API_BASE_URL:
        st.session_state.API_BASE_URL = api_url
        st.sidebar.success("API URL updated!")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Info")
    st.sidebar.info("This is a testing UI. All operations use API endpoints.")
    
    # Main content
    if page == "Games":
        page_games()
    elif page == "Books":
        page_books()
    elif page == "Status":
        page_status()


if __name__ == "__main__":
    main()
