"""
Explanation Agent - Generates human-readable explanations for chess mistakes using Groq LLM.
"""
from typing import Dict, Any, Optional, List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.models.game import MoveReview, EngineAnalysis
from app.models.base import SessionLocal
from app.schemas.llm_output import ExplanationOutput
from app.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)


class ExplanationAgent:
    """Agent for generating move explanations using Groq LLM."""

    # Generate explanations for ALL moves (not just mistakes)
    EXPLANATION_LABELS = ["Best", "Good", "Inaccuracy", "Mistake", "Blunder"]

    def __init__(self):
        """Initialize explanation agent with Groq LLM."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        self.llm = ChatGroq(
            model=settings.groq_model,
            groq_api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        # Create structured output LLM
        self.structured_llm = self.llm.with_structured_output(ExplanationOutput)

        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert chess coach providing detailed move analysis. Your comments must be:
- SPECIFIC and TACTICAL: Explain the exact chess reason why the move is good/bad
- Focus on concrete chess concepts: piece traps, tactical sequences, weak squares, king safety, piece coordination
- Avoid vague statements like "allows White to gain advantage" - explain HOW and WHY
- Maximum 4 sentences, but be detailed and educational
- Use Standard Algebraic Notation (SAN) for moves
- Analyze the position deeply to understand tactical and positional implications

**CRITICAL: Always identify whose turn it is (White or Black) and write from that player's perspective.**

**EVALUATION UNDERSTANDING:**
- Positive evaluation (+X.XX) = White has the advantage
- Negative evaluation (-X.XX) = Black has the advantage
- Higher absolute value = bigger advantage
- If {active_player} plays a move and evaluation becomes +4.39, this means {active_player} gave White a huge advantage (bad for {active_player})
- If {active_player} plays a move and evaluation becomes -2.50, this means {active_player} gave Black an advantage (good for {active_player})
- Always interpret evaluations from the perspective of who just moved

**ANALYSIS REQUIREMENTS:**
- Look at the position (FEN) and identify specific tactical elements:
  * Trapped pieces (pieces that can be captured)
  * Pins, forks, discovered attacks
  * Weak squares (especially around the king)
  * Piece coordination issues
  * Tactical sequences that the opponent can play
- Explain WHY the move creates these problems or opportunities
- Compare to the best move and explain what specific tactical/positional element was missed

Comment format:
- Start with "{active_player} played {played_move_san}"
- Explain the SPECIFIC tactical or positional reason (e.g., "the queen becomes trapped after White's Rc1", "this weakens the f7 square allowing a knight fork", "this loses the bishop to a discovered attack")
- If it's a mistake/blunder, explain the exact tactical sequence or positional weakness created
- Compare to the best move and explain what specific opportunity was missed
- Always mention the best move explicitly
- When referring to pieces, use "White's queen" or "Black's queen" to be clear
- Be SPECIFIC: Instead of "allows White to gain advantage", say "the queen becomes trapped after White's Rc1, losing material" or "this weakens the kingside allowing a mating attack"

Example for a blunder: "Black played Qxb2. This is a blunder because the queen becomes trapped after White's Rc1, which attacks the queen and forces it to retreat, losing material. Best move is Qb6, which maintains the queen's mobility and keeps it safe from immediate threats."

Always analyze the position deeply and explain specific tactical or positional reasons, not just evaluation numbers.""",
                ),
                (
                    "human",
                    """Analyze this chess move:

Position (FEN): {fen}
Active player: {active_player} (This is {active_player}'s turn - they just played this move)
Move played: {played_move_san} (Evaluation after move: {played_move_eval})
Best move: {best_move_san} (Evaluation after best move: {best_move_eval})
Move quality: {label}
{top_moves_context}

**EVALUATION INTERPRETATION:**
- The evaluation after {active_player}'s move is {played_move_eval}
- {evaluation_interpretation}
- Compare this to the best move evaluation: {best_move_eval}
- The move quality is: {label}

**IMPORTANT: The active player is {active_player}. Write your comment from {active_player}'s perspective.**

Provide a SPECIFIC comment on {active_player}'s move ({played_move_san}) following the format:
- Start with "{active_player} played {played_move_san}"
- Explain WHY this specific move is {label_lower}
- If it's a mistake/blunder, explain what specific tactical or positional problem it creates (trapped pieces, weak squares, tactical sequences, etc.)
- Compare to the best move ({best_move_san}) and explain what {active_player} missed
- Be specific about chess concepts: mention specific pieces, squares, tactical patterns, or positional weaknesses

Example for a blunder: "Black played Qxb2. This is a blunder because the queen becomes trapped after White's response. Best move is Qb5, which maintains the queen's mobility and creates threats against White's position."

Always be educational and mention specific chess concepts. Always refer to pieces as "{active_player}'s [piece]" or "the opponent's [piece]" to maintain clarity.""",
                ),
            ]
        )

        self.chain = self.prompt_template | self.structured_llm

    def _convert_uci_to_san(self, uci_move: str, fen: str) -> str:
        """
        Convert UCI move to SAN notation.

        Args:
            uci_move: Move in UCI format (e.g., "e2e4")
            fen: Position FEN string

        Returns:
            Move in SAN format (e.g., "e4")
        """
        try:
            import chess
            board = chess.Board(fen)
            move = chess.Move.from_uci(uci_move)
            return board.san(move)
        except Exception as e:
            logger.warning(f"Error converting UCI to SAN: {e}, using UCI")
            return uci_move

    def _get_active_player(self, fen: str) -> str:
        """
        Determine whose turn it is from FEN position.
        
        Note: The FEN is the position BEFORE the move, so:
        - If FEN shows "w" (white's turn), white is about to move (white will play the move)
        - If FEN shows "b" (black's turn), black is about to move (black will play the move)

        Args:
            fen: Position FEN string (before the move)

        Returns:
            "White" or "Black" - the player who is about to play (or just played) the move
        """
        try:
            import chess
            board = chess.Board(fen)
            # FEN format: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            # The "w" or "b" indicates whose turn it is to move
            # Since this is BEFORE the move, board.turn tells us who is about to move
            if board.turn == chess.WHITE:
                # It's white's turn, so white is about to play (or just played) this move
                return "White"
            else:
                # It's black's turn, so black is about to play (or just played) this move
                return "Black"
        except Exception as e:
            logger.warning(f"Error determining active player from FEN: {e}")
            return "Unknown"

    def _interpret_evaluation(self, eval_str: str, active_player: str) -> str:
        """
        Interpret evaluation from the active player's perspective.

        Args:
            eval_str: Evaluation string (e.g., "+4.39", "-2.50", "M2")
            active_player: "White" or "Black" - who just played the move

        Returns:
            Interpretation string explaining what the evaluation means for the active player
        """
        try:
            from app.services.move_classification_service import MoveClassificationService
            
            # Parse evaluation
            eval_cp = MoveClassificationService.parse_evaluation(eval_str)
            eval_pawns = eval_cp / 100.0
            
            # Check for mate
            if "M" in eval_str.upper():
                mate_moves = int(eval_str.replace("M", "").replace("+", "").replace("-", ""))
                if active_player == "White":
                    if eval_cp > 0:
                        return f"White is winning and can checkmate in {mate_moves} moves. This is excellent for White."
                    else:
                        return f"Black is winning and can checkmate in {abs(mate_moves)} moves. This is terrible for White."
                else:  # Black
                    if eval_cp < 0:
                        return f"Black is winning and can checkmate in {abs(mate_moves)} moves. This is excellent for Black."
                    else:
                        return f"White is winning and can checkmate in {mate_moves} moves. This is terrible for Black."
            
            # Interpret from active player's perspective
            if active_player == "White":
                if eval_pawns > 2.0:
                    return f"White has a winning advantage (+{eval_pawns:.2f}). This is excellent for White."
                elif eval_pawns > 0.5:
                    return f"White has a significant advantage (+{eval_pawns:.2f}). This is good for White."
                elif eval_pawns > -0.5:
                    return f"The position is roughly equal ({eval_pawns:+.2f}). This is acceptable for White."
                elif eval_pawns > -2.0:
                    return f"Black has a significant advantage ({eval_pawns:.2f}). This is bad for White."
                else:
                    return f"Black has a winning advantage ({eval_pawns:.2f}). This is terrible for White."
            else:  # Black
                if eval_pawns < -2.0:
                    return f"Black has a winning advantage ({eval_pawns:.2f}). This is excellent for Black."
                elif eval_pawns < -0.5:
                    return f"Black has a significant advantage ({eval_pawns:.2f}). This is good for Black."
                elif eval_pawns < 0.5:
                    return f"The position is roughly equal ({eval_pawns:+.2f}). This is acceptable for Black."
                elif eval_pawns < 2.0:
                    return f"White has a significant advantage (+{eval_pawns:.2f}). This is bad for Black."
                else:
                    return f"White has a winning advantage (+{eval_pawns:.2f}). This is terrible for Black."
        except Exception as e:
            logger.warning(f"Error interpreting evaluation: {e}")
            return f"Evaluation: {eval_str} (interpret from {active_player}'s perspective)"

    async def generate_explanation(
        self,
        fen: str,
        played_move: str,
        best_move: str,
        label: str,
        eval_change: str,
        top_moves: Optional[List[Dict[str, Any]]] = None,
        played_move_eval: Optional[str] = None,
        best_move_eval: Optional[str] = None,
    ) -> str:
        """
        Generate explanation for a move.

        Args:
            fen: Position FEN before move
            played_move: Move played (UCI format)
            best_move: Best move (UCI format)
            label: Move classification (Inaccuracy/Mistake/Blunder)
            eval_change: Evaluation change description
            top_moves: List of top 5 moves with evaluations
            played_move_eval: Evaluation of played move
            best_move_eval: Evaluation of best move

        Returns:
            Explanation text (max 4 sentences)
        """
        try:
            # Convert UCI to SAN
            played_move_san = self._convert_uci_to_san(played_move, fen)
            best_move_san = self._convert_uci_to_san(best_move, fen)

            # Determine whose turn it is (who just played this move)
            active_player = self._get_active_player(fen)

            # Parse evaluations to provide interpretation
            played_eval_str = played_move_eval or eval_change.split("->")[-1].strip() if "->" in eval_change else "N/A"
            best_eval_str = best_move_eval or eval_change.split("->")[0].strip() if "->" in eval_change else "N/A"
            
            # Interpret evaluation from the active player's perspective
            evaluation_interpretation = self._interpret_evaluation(played_eval_str, active_player)
            
            # Format label for prompt (lowercase)
            label_lower = label.lower() if label else "unknown"

            # Build top moves context
            top_moves_context = ""
            if top_moves:
                top_moves_context = "Top engine moves in this position:\n"
                for i, move_info in enumerate(top_moves[:5], 1):
                    move_san = move_info.get("move_san", move_info.get("move", "N/A"))
                    eval_str = move_info.get("eval_str", "N/A")
                    top_moves_context += f"{i}. {move_san} (Evaluation: {eval_str})\n"
            else:
                top_moves_context = "Top engine moves: Not available"

            # Invoke chain with structured output
            logger.debug(f"[AGENT] ExplanationAgent - Invoking LLM chain for move analysis")
            logger.debug(f"[AGENT] ExplanationAgent - Input: fen={fen[:50]}..., played_move={played_move_san}, best_move={best_move_san}, label={label}")
            logger.debug(f"[AGENT] ExplanationAgent - Active player: {active_player}, evaluation: {played_eval_str} vs {best_eval_str}")
            
            result = await self.chain.ainvoke(
                {
                    "fen": fen,
                    "active_player": active_player,
                    "played_move_san": played_move_san,
                    "best_move_san": best_move_san,
                    "label": label,
                    "label_lower": label_lower,
                    "eval_change": eval_change,
                    "top_moves_context": top_moves_context,
                    "played_move_eval": played_eval_str,
                    "best_move_eval": best_eval_str,
                    "evaluation_interpretation": evaluation_interpretation,
                }
            )
            
            logger.debug(f"[AGENT] ExplanationAgent - LLM chain completed, extracting structured output")

            # Extract explanation from structured output
            explanation = result.explanation.strip()
            logger.debug(f"[AGENT] ExplanationAgent - Generated explanation length: {len(explanation)} characters")
            if len(explanation) > 500:  # Safety check
                explanation = explanation[:500] + "..."

            return explanation
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            # Fallback explanation - check if played move is the best move
            try:
                played_move_san = self._convert_uci_to_san(played_move, fen)
                best_move_san = self._convert_uci_to_san(best_move, fen)
                active_player = self._get_active_player(fen)
                
                # If played move is the best move, give positive feedback
                if played_move == best_move or played_move_san == best_move_san:
                    return f"{active_player} played {played_move_san}. This is the best move in this position."
                else:
                    # Not the best move - explain what was missed
                    return f"{active_player} played {played_move_san}. This is not the best move. The best move is {best_move_san}, which would have been stronger."
            except Exception as fallback_error:
                logger.error(f"Error in fallback explanation: {fallback_error}")
                # Ultimate fallback - use UCI if SAN conversion fails
                if played_move == best_move:
                    return f"This is the best move in this position."
                else:
                    return f"This move is not optimal. The best move is {best_move}."

    async def explain_move(
        self, game_id: str, ply: int, use_cache: bool = True
    ) -> Optional[str]:
        """
        Generate explanation for a specific move in a game.

        Args:
            game_id: Unique game identifier
            ply: Half-move number
            use_cache: Whether to use cached explanation

        Returns:
            Explanation text or None if move doesn't need explanation
        """
        db = SessionLocal()
        try:
            # Get move review
            move_review = (
                db.query(MoveReview)
                .filter(
                    MoveReview.game_id == game_id,
                    MoveReview.ply == ply,
                )
                .first()
            )

            if not move_review:
                logger.warning(f"MoveReview not found for game {game_id}, ply {ply}")
                return None

            # Check if explanation already exists
            if use_cache and move_review.explanation:
                return move_review.explanation

            # Generate explanation for all moves
            # (EXPLANATION_LABELS now includes all labels)

            # Get engine analysis for context
            engine_analysis = (
                db.query(EngineAnalysis)
                .filter(
                    EngineAnalysis.game_id == game_id,
                    EngineAnalysis.ply == ply,
                )
                .first()
            )

            if not engine_analysis:
                logger.warning(
                    f"EngineAnalysis not found for game {game_id}, ply {ply}"
                )
                return None

            # Generate explanation with top moves data
            eval_change = f"{engine_analysis.eval_before} -> {engine_analysis.eval_after}"
            top_moves = engine_analysis.top_moves if hasattr(engine_analysis, 'top_moves') and engine_analysis.top_moves else None
            played_move_eval = engine_analysis.played_move_eval if hasattr(engine_analysis, 'played_move_eval') else None
            best_move_eval = engine_analysis.eval_best
            
            explanation = await self.generate_explanation(
                fen=engine_analysis.fen,
                played_move=engine_analysis.played_move,
                best_move=engine_analysis.best_move,
                label=move_review.label,
                eval_change=eval_change,
                top_moves=top_moves,
                played_move_eval=played_move_eval,
                best_move_eval=best_move_eval,
            )

            # Update move review with explanation
            move_review.explanation = explanation
            db.commit()

            logger.info(f"Generated explanation for game {game_id}, ply {ply}")
            return explanation
        except Exception as e:
            db.rollback()
            logger.error(f"Error explaining move: {e}")
            raise
        finally:
            db.close()

    async def explain_game_moves(
        self, game_id: str, use_cache: bool = True
    ) -> Dict[int, str]:
        """
        Generate explanations for all moves in a game (parallelized).

        Args:
            game_id: Unique game identifier
            use_cache: Whether to use cached explanations

        Returns:
            Dictionary mapping ply -> explanation
        """
        db = SessionLocal()
        try:
            # Get all moves (generate explanations for all moves)
            move_reviews = (
                db.query(MoveReview)
                .filter(MoveReview.game_id == game_id)
                .order_by(MoveReview.ply)
                .all()
            )

            # Separate cached and uncached moves
            cached_explanations = {}
            moves_to_generate = []
            
            for move_review in move_reviews:
                if use_cache and move_review.explanation:
                    cached_explanations[move_review.ply] = move_review.explanation
                else:
                    moves_to_generate.append(move_review.ply)

            if not moves_to_generate:
                logger.info(
                    f"All explanations cached for game {game_id} ({len(cached_explanations)} moves)"
                )
                return cached_explanations

            # Parallelize explanation generation with concurrency limit
            concurrency_limit = settings.explanation_concurrency
            semaphore = asyncio.Semaphore(concurrency_limit)
            
            async def explain_with_semaphore(ply: int) -> tuple[int, Optional[str]]:
                """Generate explanation with semaphore to limit concurrency."""
                async with semaphore:
                    try:
                        explanation = await self.explain_move(
                            game_id, ply, use_cache=False
                        )
                        return (ply, explanation)
                    except Exception as e:
                        logger.error(
                            f"Error explaining ply {ply}: {e}, skipping"
                        )
                        return (ply, None)

            # Generate all explanations in parallel
            logger.info(
                f"[AGENT] ExplanationAgent - Generating {len(moves_to_generate)} explanations in parallel "
                f"(concurrency: {concurrency_limit}) for game {game_id}"
            )
            logger.debug(f"[AGENT] ExplanationAgent - Moves to generate: {moves_to_generate}")
            logger.debug(f"[AGENT] ExplanationAgent - Creating {len(moves_to_generate)} parallel tasks")
            
            tasks = [explain_with_semaphore(ply) for ply in moves_to_generate]
            logger.debug(f"[AGENT] ExplanationAgent - Executing {len(tasks)} tasks with asyncio.gather()")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug(f"[AGENT] ExplanationAgent - All parallel tasks completed, processing {len(results)} results")
            
            # Combine results
            explanations = cached_explanations.copy()
            generated_count = 0
            error_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"Unexpected error in parallel explanation: {result}")
                    continue
                
                ply, explanation = result
                if explanation:
                    explanations[ply] = explanation
                    generated_count += 1

            logger.info(
                f"Generated {generated_count} explanations for game {game_id} "
                f"({len(cached_explanations)} cached, {error_count} errors, "
                f"total: {len(explanations)}/{len(move_reviews)})"
            )
            return explanations
        finally:
            db.close()
