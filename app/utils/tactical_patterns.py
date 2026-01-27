"""
Tactical Pattern Detector - Identifies specific tactical elements in chess positions.
Detects pins, forks, discovered attacks, hanging pieces, and weak squares.
"""
from typing import Dict, Any, List, Optional
import chess
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TacticalPatternDetector:
    """Detector for tactical patterns in chess positions."""

    @staticmethod
    def detect_pins(board: chess.Board) -> List[Dict[str, Any]]:
        """
        Detect pinned pieces in the position.

        Args:
            board: chess.Board object

        Returns:
            List of pin information dictionaries:
            [
                {
                    "piece": str,  # "knight", "queen", etc.
                    "square": str,  # "f3"
                    "pinned_by": str,  # "bishop", "rook", "queen"
                    "pinned_to": str,  # "king", "queen", etc.
                    "pinning_piece_square": str,  # Square of pinning piece
                    "color": str  # "white" or "black"
                }
            ]
        """
        pins = []
        
        # Check for pins from both sides
        for color in [chess.WHITE, chess.BLACK]:
            # Get all pieces of this color
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.color == color:
                    # Check if this piece is pinned
                    pin_info = TacticalPatternDetector._check_pin(board, square, color)
                    if pin_info:
                        pins.append(pin_info)
        
        return pins

    @staticmethod
    def _check_pin(board: chess.Board, square: int, color: bool) -> Optional[Dict[str, Any]]:
        """Check if a piece on a square is pinned."""
        piece = board.piece_at(square)
        if not piece or piece.piece_type == chess.KING:
            return None
        
        # Try removing the piece and see if king is in check
        board_copy = board.copy()
        board_copy.remove_piece_at(square)
        
        # Check if king is now in check
        if board_copy.is_check():
            # Find what's attacking the king
            attackers = list(board_copy.attackers(not color, board_copy.king(color)))
            if attackers:
                attacker_square = attackers[0]
                attacker_piece = board_copy.piece_at(attacker_square)
                
                # Determine pinning piece type
                pinning_piece_type = TacticalPatternDetector._get_piece_name(attacker_piece)
                
                # Determine what the piece is pinned to (usually king)
                pinned_to = "king"  # Default assumption
                
                return {
                    "piece": TacticalPatternDetector._get_piece_name(piece),
                    "square": chess.square_name(square),
                    "pinned_by": pinning_piece_type,
                    "pinned_to": pinned_to,
                    "pinning_piece_square": chess.square_name(attacker_square),
                    "color": "white" if color == chess.WHITE else "black"
                }
        
        return None

    @staticmethod
    def detect_forks(board: chess.Board) -> List[Dict[str, Any]]:
        """
        Detect fork opportunities (pieces that can attack multiple targets).

        Args:
            board: chess.Board object

        Returns:
            List of fork information:
            [
                {
                    "attacker": str,  # "knight", "pawn", etc.
                    "square": str,  # Square where fork can occur
                    "targets": List[str],  # ["queen", "rook"]
                    "target_squares": List[str],  # ["d5", "f7"]
                    "color": str
                }
            ]
        """
        forks = []
        active_color = board.turn
        
        # Check all legal moves for fork opportunities
        for move in board.legal_moves:
            board_copy = board.copy()
            board_copy.push(move)
            
            # Check if this move attacks multiple pieces
            attacked_pieces = TacticalPatternDetector._get_attacked_pieces(
                board_copy, move.to_square, active_color
            )
            
            if len(attacked_pieces) >= 2:
                moving_piece = board.piece_at(move.from_square)
                forks.append({
                    "attacker": TacticalPatternDetector._get_piece_name(moving_piece),
                    "square": chess.square_name(move.to_square),
                    "targets": [p["piece"] for p in attacked_pieces],
                    "target_squares": [p["square"] for p in attacked_pieces],
                    "color": "white" if active_color == chess.WHITE else "black"
                })
        
        return forks

    @staticmethod
    def _get_attacked_pieces(board: chess.Board, square: int, color: bool) -> List[Dict[str, Any]]:
        """Get pieces attacked from a square."""
        attacked = []
        
        # Get all squares attacked from this square
        attacked_squares = board.attacks(square)
        
        for attacked_square in attacked_squares:
            piece = board.piece_at(attacked_square)
            if piece and piece.color != color:  # Enemy piece
                attacked.append({
                    "piece": TacticalPatternDetector._get_piece_name(piece),
                    "square": chess.square_name(attacked_square)
                })
        
        return attacked

    @staticmethod
    def detect_discovered_attacks(board: chess.Board) -> List[Dict[str, Any]]:
        """
        Detect discovered attack opportunities.

        Args:
            board: chess.Board object

        Returns:
            List of discovered attack information:
            [
                {
                    "discovering_piece": str,
                    "discovering_square": str,
                    "attacking_piece": str,
                    "target": str,
                    "target_square": str,
                    "color": str
                }
            ]
        """
        discovered_attacks = []
        active_color = board.turn
        
        # Check all legal moves for discovered attacks
        for move in board.legal_moves:
            moving_piece = board.piece_at(move.from_square)
            
            # Check if moving this piece reveals an attack
            board_copy = board.copy()
            board_copy.push(move)
            
            # Find pieces that can now attack (that couldn't before)
            # This is simplified - in practice, we'd check if a piece behind
            # the moved piece can now attack
            # For now, we'll check if any piece can attack enemy pieces after the move
            for square in chess.SQUARES:
                piece = board_copy.piece_at(square)
                if piece and piece.color == active_color:
                    # Check what this piece attacks
                    attacked = TacticalPatternDetector._get_attacked_pieces(
                        board_copy, square, active_color
                    )
                    
                    # Check if this attack wasn't possible before the move
                    # (simplified check - in practice would be more complex)
                    if attacked and moving_piece.piece_type != piece.piece_type:
                        for target in attacked:
                            discovered_attacks.append({
                                "discovering_piece": TacticalPatternDetector._get_piece_name(moving_piece),
                                "discovering_square": chess.square_name(move.from_square),
                                "attacking_piece": TacticalPatternDetector._get_piece_name(piece),
                                "target": target["piece"],
                                "target_square": target["square"],
                                "color": "white" if active_color == chess.WHITE else "black"
                            })
        
        # Remove duplicates
        seen = set()
        unique_attacks = []
        for attack in discovered_attacks:
            key = (attack["discovering_square"], attack["target_square"])
            if key not in seen:
                seen.add(key)
                unique_attacks.append(attack)
        
        return unique_attacks[:5]  # Limit to 5 most relevant

    @staticmethod
    def detect_hanging_pieces(board: chess.Board) -> List[Dict[str, Any]]:
        """
        Detect hanging (undefended or poorly defended) pieces.

        Args:
            board: chess.Board object

        Returns:
            List of hanging piece information:
            [
                {
                    "piece": str,
                    "square": str,
                    "attacked_by": List[str],  # Pieces attacking it
                    "defended_by": List[str],  # Pieces defending it
                    "color": str,
                    "is_hanging": bool  # True if attacked more than defended
                }
            ]
        """
        hanging_pieces = []
        active_color = board.turn
        
        # Check all pieces of the opponent
        opponent_color = not active_color
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == opponent_color:
                # Count attackers and defenders
                attackers = list(board.attackers(active_color, square))
                defenders = list(board.attackers(opponent_color, square))
                
                # Piece is hanging if attacked more than defended
                # (simplified - doesn't account for piece values)
                is_hanging = len(attackers) > len(defenders)
                
                if is_hanging or len(attackers) > 0:
                    attacked_by = [
                        TacticalPatternDetector._get_piece_name(board.piece_at(att))
                        for att in attackers
                    ]
                    defended_by = [
                        TacticalPatternDetector._get_piece_name(board.piece_at(def_sq))
                        for def_sq in defenders
                    ]
                    
                    hanging_pieces.append({
                        "piece": TacticalPatternDetector._get_piece_name(piece),
                        "square": chess.square_name(square),
                        "attacked_by": attacked_by,
                        "defended_by": defended_by,
                        "color": "white" if opponent_color == chess.WHITE else "black",
                        "is_hanging": is_hanging
                    })
        
        return hanging_pieces

    @staticmethod
    def detect_weak_squares(board: chess.Board) -> List[str]:
        """
        Detect weak squares (especially around the king).

        Args:
            board: chess.Board object

        Returns:
            List of weak square names: ["f7", "g6"]
        """
        weak_squares = []
        
        # Check squares around both kings
        for color in [chess.WHITE, chess.BLACK]:
            king_square = board.king(color)
            if king_square is None:
                continue
            
            king_rank = chess.square_rank(king_square)
            king_file = chess.square_file(king_square)
            
            # Check squares around king (±1 file, ±1 rank)
            for file_offset in [-1, 0, 1]:
                for rank_offset in [-1, 0, 1]:
                    if file_offset == 0 and rank_offset == 0:
                        continue  # Skip king's square
                    
                    check_file = king_file + file_offset
                    check_rank = king_rank + rank_offset
                    
                    if 0 <= check_file <= 7 and 0 <= check_rank <= 7:
                        square = chess.square(check_file, check_rank)
                        square_name = chess.square_name(square)
                        
                        # Check if square is weak (not defended by pawns)
                        is_defended_by_pawn = False
                        for defender_square in board.attackers(color, square):
                            defender = board.piece_at(defender_square)
                            if defender and defender.piece_type == chess.PAWN:
                                is_defended_by_pawn = True
                                break
                        
                        if not is_defended_by_pawn:
                            # Check if enemy can attack this square
                            enemy_color = not color
                            attackers = list(board.attackers(enemy_color, square))
                            if attackers:
                                weak_squares.append(square_name)
        
        return list(set(weak_squares))  # Remove duplicates

    @staticmethod
    def _get_piece_name(piece: Optional[chess.Piece]) -> str:
        """Get human-readable piece name."""
        if not piece:
            return "unknown"
        
        piece_names = {
            chess.PAWN: "pawn",
            chess.KNIGHT: "knight",
            chess.BISHOP: "bishop",
            chess.ROOK: "rook",
            chess.QUEEN: "queen",
            chess.KING: "king",
        }
        
        return piece_names.get(piece.piece_type, "unknown")

    @staticmethod
    def identify_tactical_patterns(board: chess.Board) -> List[str]:
        """
        Identify all tactical patterns and return as list of descriptions.

        Args:
            board: chess.Board object

        Returns:
            List of tactical pattern descriptions:
            [
                "pin: bishop pins knight on f3 to king",
                "hanging: black queen on d5",
                "weak square: f7 is vulnerable"
            ]
        """
        patterns = []
        
        # Detect pins
        pins = TacticalPatternDetector.detect_pins(board)
        for pin in pins[:3]:  # Limit to 3 most relevant
            patterns.append(
                f"pin: {pin['pinned_by']} on {pin['pinning_piece_square']} pins "
                f"{pin['color']} {pin['piece']} on {pin['square']} to {pin['pinned_to']}"
            )
        
        # Detect forks
        forks = TacticalPatternDetector.detect_forks(board)
        for fork in forks[:3]:  # Limit to 3 most relevant
            targets_str = " and ".join(fork['targets'])
            patterns.append(
                f"fork: {fork['color']} {fork['attacker']} on {fork['square']} can fork {targets_str}"
            )
        
        # Detect hanging pieces
        hanging = TacticalPatternDetector.detect_hanging_pieces(board)
        for hang in hanging[:3]:  # Limit to 3 most relevant
            if hang['is_hanging']:
                patterns.append(
                    f"hanging: {hang['color']} {hang['piece']} on {hang['square']} is hanging"
                )
        
        # Detect weak squares
        weak_squares = TacticalPatternDetector.detect_weak_squares(board)
        for square in weak_squares[:3]:  # Limit to 3 most relevant
            patterns.append(f"weak square: {square} is vulnerable")
        
        return patterns
