"""
Chess Principles Knowledge Base - Reference guide for chess concepts.
Contains Silman's Imbalances, Fine's Principles, tactical motifs, and strategic concepts.
"""
from typing import Dict, List

# Silman's 7 Imbalances
SILMAN_IMBALANCES = {
    "material": "Material imbalance refers to differences in piece values. A player may sacrifice material for positional advantages like initiative, piece activity, or king safety.",
    "minor_pieces": "Minor piece imbalances (knights vs bishops) affect the nature of the position. Knights excel in closed positions, bishops in open positions.",
    "pawn_structure": "Pawn structure imbalances include doubled pawns, isolated pawns, passed pawns, and pawn chains. These affect piece mobility and weak squares.",
    "space": "Space advantage means controlling more squares, especially in the center. This restricts the opponent's pieces and creates attacking opportunities.",
    "piece_activity": "Piece activity imbalance refers to how well pieces are placed. Active pieces control more squares and coordinate better than passive ones.",
    "king_safety": "King safety imbalance is critical. An exposed king is vulnerable to attack, while a safe king allows pieces to focus on other tasks.",
    "initiative": "Initiative imbalance means one side has the ability to create threats and force the opponent to react defensively."
}

# Fine's 30 Principles (selected key principles)
FINE_PRINCIPLES = {
    "development": "Develop pieces quickly and efficiently. Knights before bishops, control the center, castle early.",
    "center_control": "Control the center squares (e4, e5, d4, d5) with pawns and pieces. Central control provides mobility and attacking options.",
    "king_safety": "Keep the king safe, especially in the opening and middlegame. Castle early, maintain pawn shield, avoid exposing the king.",
    "piece_coordination": "Coordinate pieces to work together. Pieces should support each other and create threats in combination.",
    "weak_squares": "Weak squares are squares that cannot be defended by pawns. They provide outposts for enemy pieces.",
    "pawn_structure": "Maintain a healthy pawn structure. Avoid doubled, isolated, or backward pawns when possible.",
    "piece_activity": "Keep pieces active. Passive pieces are less valuable than active ones. Centralize pieces when possible.",
    "material": "Material advantage usually wins, but positional factors can compensate. Don't sacrifice material without compensation.",
    "tactics": "Always look for tactical opportunities: pins, forks, discovered attacks, skewers, and combinations.",
    "endgame": "In the endgame, king activity is crucial. Centralize the king, create passed pawns, and use opposition."
}

# Common Tactical Motifs
TACTICAL_MOTIFS = {
    "pin": "A pin occurs when a piece cannot move without exposing a more valuable piece behind it. The pinned piece is vulnerable to attack.",
    "fork": "A fork attacks two or more pieces simultaneously with one move. Knights are excellent forking pieces.",
    "skewer": "A skewer is like a pin in reverse - a more valuable piece is attacked and must move, exposing a less valuable piece behind it.",
    "discovered_attack": "A discovered attack occurs when moving one piece reveals an attack by another piece behind it.",
    "discovered_check": "A discovered check is a discovered attack that checks the opponent's king, forcing a response.",
    "double_attack": "A double attack threatens two targets at once, often forcing the opponent to lose material.",
    "deflection": "Deflection forces a piece away from an important square or duty, often to enable a tactical combination.",
    "decoy": "A decoy lures an enemy piece to a bad square, usually to enable a tactical combination.",
    "overloading": "Overloading occurs when a piece has too many defensive duties and cannot protect all of them.",
    "removing_defender": "Removing the defender eliminates a piece that protects another piece or square, enabling tactics.",
    "back_rank_weakness": "Back rank weakness occurs when the king is trapped by its own pawns, vulnerable to back rank mate.",
    "windmill": "A windmill is a series of checks and captures that win material, often involving a rook and bishop.",
    "zugzwang": "Zugzwang is a position where any move weakens the position. Common in endgames.",
    "zwischenzug": "Zwischenzug (in-between move) is a tactical intermezzo that improves the position before completing a combination.",
    "x_ray": "An X-ray attack sees through pieces to attack a target behind them, often involving rooks or queens.",
    "battery": "A battery is two pieces on the same line (rank, file, or diagonal) that can combine for a powerful attack.",
    "clearance": "Clearance sacrifices a piece to clear a square or line for another piece to use.",
    "interference": "Interference blocks the connection between two enemy pieces, often breaking a defensive formation.",
    "trapping": "Trapping occurs when a piece has no safe squares to move to and can be captured.",
    "hanging_piece": "A hanging piece is undefended or poorly defended and can be captured."
}

# Positional Principles
POSITIONAL_PRINCIPLES = {
    "weak_squares": "Weak squares are squares that cannot be defended by pawns. They provide excellent outposts for knights and other pieces.",
    "outpost": "An outpost is a square, usually in enemy territory, that is protected by a pawn and cannot be attacked by enemy pawns.",
    "pawn_chain": "A pawn chain is a group of connected pawns. The base of the chain is the weakest point.",
    "isolated_pawn": "An isolated pawn has no friendly pawns on adjacent files. It's weak because it cannot be defended by other pawns.",
    "doubled_pawn": "Doubled pawns are two pawns of the same color on the same file. They're often weak but can control squares.",
    "passed_pawn": "A passed pawn has no enemy pawns in front of it or on adjacent files. It's a powerful endgame asset.",
    "backward_pawn": "A backward pawn is behind other pawns and cannot advance safely. It's often a weakness.",
    "pawn_island": "A pawn island is a group of connected pawns separated from other pawns. More islands usually means more weaknesses.",
    "bad_bishop": "A bad bishop is blocked by its own pawns, limiting its mobility. Often occurs in closed positions.",
    "good_bishop": "A good bishop has open diagonals and is not blocked by its own pawns. More valuable than a bad bishop.",
    "piece_centralization": "Centralized pieces control more squares and are more active. Centralize pieces when possible.",
    "open_file": "An open file has no pawns. Rooks are most effective on open files, especially near the enemy king.",
    "semi_open_file": "A semi-open file has only enemy pawns. Rooks can pressure these pawns effectively.",
    "pawn_break": "A pawn break advances a pawn to challenge the opponent's pawn structure, often opening lines.",
    "weak_color_complex": "A weak color complex is a group of squares of the same color that are weak, often around the king."
}

# Endgame Principles
ENDGAME_PRINCIPLES = {
    "king_activity": "In the endgame, the king becomes a strong piece. Centralize the king and use it actively.",
    "opposition": "Opposition is a key endgame concept where kings face each other with one square between them. The player not to move has the opposition.",
    "passed_pawn": "Passed pawns are crucial in endgames. Push them forward, support them with the king, and they often decide the game.",
    "rook_endgames": "In rook endgames, active rooks and king activity are essential. Rooks belong behind passed pawns.",
    "bishop_vs_knight": "Bishops are usually better in open positions with pawns on both sides. Knights excel in closed positions.",
    "pawn_endgames": "In pawn endgames, king activity, opposition, and zugzwang are critical concepts.",
    "queen_endgames": "In queen endgames, perpetual check is a common drawing resource. Be careful of stalemate.",
    "minor_piece_endgames": "In minor piece endgames, the bishop pair is usually stronger than bishop and knight or two knights."
}

# Opening Principles
OPENING_PRINCIPLES = {
    "center_control": "Control the center with pawns (e4, d4, e5, d5) and develop pieces toward the center.",
    "rapid_development": "Develop pieces quickly. Don't move the same piece twice in the opening without good reason.",
    "king_safety": "Castle early to protect the king and connect the rooks.",
    "piece_coordination": "Develop pieces to squares where they work together and control important squares.",
    "avoid_premature_attacks": "Don't launch attacks before completing development. Complete development first.",
    "connect_rooks": "Connect the rooks by moving pieces off the back rank. This improves coordination."
}

# Combined knowledge base
CHESS_PRINCIPLES = {
    "silman_imbalances": SILMAN_IMBALANCES,
    "fine_principles": FINE_PRINCIPLES,
    "tactical_motifs": TACTICAL_MOTIFS,
    "positional_principles": POSITIONAL_PRINCIPLES,
    "endgame_principles": ENDGAME_PRINCIPLES,
    "opening_principles": OPENING_PRINCIPLES,
}


def get_relevant_principles(theme_analysis: Dict, tactical_patterns: List[str]) -> List[str]:
    """
    Get relevant chess principles based on detected themes and tactical patterns.
    
    Args:
        theme_analysis: Dictionary with theme analysis results
        tactical_patterns: List of tactical pattern descriptions
        
    Returns:
        List of relevant principle descriptions
    """
    principles = []
    
    # Check material imbalance
    material = theme_analysis.get("material", {})
    if material.get("advantage") != "equal":
        principles.append(CHESS_PRINCIPLES["fine_principles"]["material"])
        principles.append(CHESS_PRINCIPLES["silman_imbalances"]["material"])
    
    # Check mobility
    mobility = theme_analysis.get("mobility", {})
    if mobility.get("mobility_advantage") != "equal":
        principles.append(CHESS_PRINCIPLES["fine_principles"]["piece_activity"])
        principles.append(CHESS_PRINCIPLES["silman_imbalances"]["piece_activity"])
    
    # Check space
    space = theme_analysis.get("space", {})
    if space.get("space_advantage") != "equal":
        principles.append(CHESS_PRINCIPLES["silman_imbalances"]["space"])
    
    # Check king safety
    king_safety = theme_analysis.get("king_safety", {})
    if king_safety.get("white_king_safety") in ["vulnerable", "exposed"] or \
       king_safety.get("black_king_safety") in ["vulnerable", "exposed"]:
        principles.append(CHESS_PRINCIPLES["fine_principles"]["king_safety"])
        principles.append(CHESS_PRINCIPLES["silman_imbalances"]["king_safety"])
    
    # Check tactical patterns
    for pattern in tactical_patterns:
        pattern_lower = pattern.lower()
        if "pin" in pattern_lower:
            principles.append(CHESS_PRINCIPLES["tactical_motifs"]["pin"])
        elif "fork" in pattern_lower:
            principles.append(CHESS_PRINCIPLES["tactical_motifs"]["fork"])
        elif "discovered" in pattern_lower:
            principles.append(CHESS_PRINCIPLES["tactical_motifs"]["discovered_attack"])
        elif "hanging" in pattern_lower:
            principles.append(CHESS_PRINCIPLES["tactical_motifs"]["hanging_piece"])
        elif "weak square" in pattern_lower:
            principles.append(CHESS_PRINCIPLES["positional_principles"]["weak_squares"])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_principles = []
    for principle in principles:
        if principle not in seen:
            seen.add(principle)
            unique_principles.append(principle)
    
    return unique_principles[:5]  # Limit to 5 most relevant
