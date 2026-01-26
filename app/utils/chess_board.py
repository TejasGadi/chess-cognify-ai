"""
Chess board visualization utilities for Streamlit.
"""
import chess
import chess.svg
from typing import Optional, List, Dict, Any
from io import BytesIO
import base64


def render_board_svg(
    board: chess.Board,
    last_move: Optional[chess.Move] = None,
    arrows: Optional[List[tuple]] = None,
    size: int = 400
) -> str:
    """
    Render a chess board as SVG string.
    
    Args:
        board: chess.Board instance
        last_move: Optional last move to highlight
        arrows: Optional list of arrows to draw (list of (from_square, to_square) tuples)
        size: Board size in pixels
    
    Returns:
        SVG string
    """
    if arrows is None:
        arrows = []
    
    # Convert arrows to chess.svg format
    svg_arrows = []
    for arrow in arrows:
        if len(arrow) == 2:
            from_sq, to_sq = arrow
            svg_arrows.append(chess.svg.Arrow(from_sq, to_sq))
    
    svg = chess.svg.board(
        board=board,
        lastmove=last_move,
        arrows=svg_arrows,
        size=size
    )
    return svg


def board_to_base64_svg(board: chess.Board, last_move: Optional[chess.Move] = None, size: int = 400) -> str:
    """
    Convert chess board to base64-encoded SVG for embedding in HTML.
    
    Returns:
        Base64-encoded SVG string
    """
    svg = render_board_svg(board, last_move=last_move, size=size)
    svg_bytes = svg.encode('utf-8')
    base64_svg = base64.b64encode(svg_bytes).decode('utf-8')
    return f"data:image/svg+xml;base64,{base64_svg}"


def pgn_to_board(pgn: str, move_number: Optional[int] = None) -> Optional[chess.Board]:
    """
    Convert PGN to a chess board at a specific move number.
    
    Args:
        pgn: PGN string
        move_number: Move number to stop at (None for final position)
    
    Returns:
        chess.Board instance or None if invalid
    """
    try:
        game = chess.pgn.read_game(chess.pgn.StringIO(pgn))
        if game is None:
            return None
        
        board = game.board()
        moves = list(game.mainline_moves())
        
        if move_number is None:
            move_number = len(moves)
        
        for i, move in enumerate(moves[:move_number]):
            board.push(move)
        
        return board
    except Exception:
        return None


def get_move_list(pgn: str) -> List[Dict[str, Any]]:
    """
    Extract move list from PGN.
    
    Returns:
        List of moves with number, color, and SAN notation
    """
    try:
        game = chess.pgn.read_game(chess.pgn.StringIO(pgn))
        if game is None:
            return []
        
        moves = []
        board = game.board()
        
        for move in game.mainline_moves():
            move_number = board.fullmove_number
            is_white = board.turn == chess.WHITE
            
            moves.append({
                "number": move_number,
                "color": "white" if is_white else "black",
                "san": board.san(move),
                "move": move
            })
            
            board.push(move)
        
        return moves
    except Exception:
        return []


def board_to_pgn(moves: List[str]) -> str:
    """
    Convert a list of moves (in SAN or UCI) to PGN format.
    
    Args:
        moves: List of move strings
    
    Returns:
        PGN string
    """
    board = chess.Board()
    pgn_moves = []
    
    for move_str in moves:
        try:
            # Try to parse as SAN first
            move = board.parse_san(move_str)
            board.push(move)
            
            # Format move for PGN
            if board.turn == chess.BLACK:
                pgn_moves.append(f"{board.fullmove_number - 1}. {move_str}")
            else:
                pgn_moves.append(move_str)
        except:
            try:
                # Try UCI format
                move = chess.Move.from_uci(move_str)
                if move in board.legal_moves:
                    board.push(move)
                    san = board.san(move)
                    if board.turn == chess.BLACK:
                        pgn_moves.append(f"{board.fullmove_number - 1}. {san}")
                    else:
                        pgn_moves.append(san)
            except:
                continue
    
    return " ".join(pgn_moves)
