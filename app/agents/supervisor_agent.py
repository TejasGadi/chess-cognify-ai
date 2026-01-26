"""
Supervisor Agent - Orchestrates the complete game review workflow.
"""
from typing import Dict, Any, Optional
import uuid
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from app.agents.state import GameReviewState, GameReviewInput, GameReviewOutput
from app.services.pgn_service import PGNService
from app.services.engine_analysis_service import EngineAnalysisService
from app.services.move_classification_service import MoveClassificationService
from app.services.accuracy_rating_service import AccuracyRatingService
from app.agents.explanation_agent import ExplanationAgent
from app.agents.weakness_detection_agent import WeaknessDetectionAgent
from app.models.game import Game
from app.models.base import SessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent:
    """Supervisor agent that orchestrates the complete game review workflow."""

    def __init__(self):
        """Initialize supervisor agent with all required services."""
        self.pgn_service = PGNService()
        self.engine_service = EngineAnalysisService()
        self.classification_service = MoveClassificationService()
        self.accuracy_service = AccuracyRatingService()
        self.explanation_agent = ExplanationAgent()
        self.weakness_agent = WeaknessDetectionAgent()

    def _create_initial_state(
        self, pgn: str, metadata: Optional[Dict[str, Any]] = None, game_id: Optional[str] = None
    ) -> GameReviewState:
        """Create initial state for workflow."""
        if game_id is None:
            game_id = str(uuid.uuid4())

        return {
            "game_id": game_id,
            "pgn": pgn,
            "metadata": metadata or {},
            "pgn_valid": False,
            "validation_error": None,
            "engine_analyses": [],
            "engine_analysis_complete": False,
            "engine_analysis_error": None,
            "classifications": [],
            "classification_complete": False,
            "classification_error": None,
            "explanations": {},
            "explanation_complete": False,
            "explanation_error": None,
            "accuracy": None,
            "estimated_rating": None,
            "rating_confidence": None,
            "accuracy_complete": False,
            "accuracy_error": None,
            "weaknesses": [],
            "weakness_detection_complete": False,
            "weakness_error": None,
            "review_complete": False,
            "review_error": None,
            "current_step": "initialized",
            "progress_percentage": 0,
        }

    async def validate_pgn(self, state: GameReviewState) -> GameReviewState:
        """Node: Validate PGN."""
        logger.info(f"Validating PGN for game {state['game_id']}")
        state["current_step"] = "validating_pgn"
        state["progress_percentage"] = 5

        try:
            is_valid, error = self.pgn_service.validate_pgn(state["pgn"])
            state["pgn_valid"] = is_valid
            state["validation_error"] = error

            if not is_valid:
                state["review_error"] = f"PGN validation failed: {error}"
                state["review_complete"] = True
                logger.error(f"PGN validation failed: {error}")
        except Exception as e:
            logger.error(f"Error validating PGN: {e}")
            state["pgn_valid"] = False
            state["validation_error"] = str(e)
            state["review_error"] = f"PGN validation error: {e}"
            state["review_complete"] = True

        return state

    async def analyze_engine(self, state: GameReviewState) -> GameReviewState:
        """Node: Engine Analysis."""
        logger.info(f"Starting engine analysis for game {state['game_id']}")
        state["current_step"] = "engine_analysis"
        state["progress_percentage"] = 20

        try:
            # Persist game first
            self._persist_game(state)

            # Analyze game
            analyses = await self.engine_service.analyze_game(
                state["pgn"], state["game_id"], use_cache=True
            )

            if not analyses or len(analyses) == 0:
                raise ValueError("Engine analysis returned no results - check Stockfish configuration")

            # Persist analyses
            await self.engine_service.persist_analysis(state["game_id"], analyses)

            state["engine_analyses"] = analyses
            state["engine_analysis_complete"] = True
            state["progress_percentage"] = 40
            logger.info(f"Engine analysis complete: {len(analyses)} moves analyzed")
        except Exception as e:
            logger.error(f"Error in engine analysis: {e}", exc_info=True)
            state["engine_analysis_error"] = str(e)
            state["engine_analysis_complete"] = False
            state["review_error"] = f"Engine analysis error: {e}"
            state["review_complete"] = True

        return state

    async def classify_moves(self, state: GameReviewState) -> GameReviewState:
        """Node: Move Classification."""
        logger.info(f"Classifying moves for game {state['game_id']}")
        state["current_step"] = "move_classification"
        state["progress_percentage"] = 50

        try:
            if not state.get("engine_analyses") or len(state["engine_analyses"]) == 0:
                raise ValueError("No engine analyses available for classification")

            # Classify moves
            classifications = self.classification_service.classify_game_moves(
                state["game_id"], state["engine_analyses"]
            )

            if not classifications or len(classifications) == 0:
                raise ValueError("Move classification returned no results")

            # Add phases
            classifications = self.classification_service.add_game_phases(
                state["game_id"], classifications, state["pgn"]
            )

            # Persist classifications
            self.classification_service.persist_classifications(
                state["game_id"], classifications
            )

            state["classifications"] = classifications
            state["classification_complete"] = True
            state["progress_percentage"] = 60
            logger.info(f"Move classification complete: {len(classifications)} moves classified")
        except Exception as e:
            logger.error(f"Error in move classification: {e}", exc_info=True)
            state["classification_error"] = str(e)
            state["classification_complete"] = False
            state["review_error"] = f"Move classification error: {e}"
            state["review_complete"] = True

        return state

    async def generate_explanations(self, state: GameReviewState) -> GameReviewState:
        """Node: Generate Explanations (conditional)."""
        logger.info(f"Generating explanations for game {state['game_id']}")
        state["current_step"] = "generating_explanations"
        state["progress_percentage"] = 70

        try:
            # Generate explanations for mistakes
            explanations = await self.explanation_agent.explain_game_moves(
                state["game_id"], use_cache=True
            )

            state["explanations"] = explanations
            state["explanation_complete"] = True
            state["progress_percentage"] = 75
            logger.info(f"Explanations complete: {len(explanations)} explanations generated")
        except Exception as e:
            logger.error(f"Error generating explanations: {e}")
            state["explanation_error"] = str(e)
            # Don't fail entire review if explanations fail
            state["explanation_complete"] = True
            state["explanations"] = {}

        return state

    async def calculate_accuracy_rating(self, state: GameReviewState) -> GameReviewState:
        """Node: Accuracy & Rating."""
        logger.info(f"Calculating accuracy and rating for game {state['game_id']}")
        state["current_step"] = "accuracy_rating"
        state["progress_percentage"] = 80

        try:
            # Calculate accuracy
            accuracy_metrics = self.accuracy_service.calculate_game_accuracy(
                state["classifications"]
            )

            # Update move accuracies
            self.accuracy_service.update_move_accuracies(
                state["game_id"], state["classifications"]
            )

            # Estimate rating
            time_control = state.get("metadata", {}).get("time_control", None)
            rating_info = self.accuracy_service.estimate_rating(
                accuracy_metrics["accuracy"],
                accuracy_metrics["blunder_count"],
                time_control,
            )

            # Persist summary
            self.accuracy_service.persist_game_summary(
                state["game_id"],
                accuracy_metrics["accuracy"],
                rating_info["estimated_rating"],
                rating_info["confidence"],
            )

            state["accuracy"] = accuracy_metrics["accuracy"]
            state["estimated_rating"] = rating_info["estimated_rating"]
            state["rating_confidence"] = rating_info["confidence"]
            state["accuracy_complete"] = True
            state["progress_percentage"] = 90
            logger.info(f"Accuracy and rating complete: {accuracy_metrics['accuracy']}% accuracy")
        except Exception as e:
            logger.error(f"Error calculating accuracy/rating: {e}")
            state["accuracy_error"] = str(e)
            state["accuracy_complete"] = False
            state["review_error"] = f"Accuracy calculation error: {e}"
            state["review_complete"] = True

        return state

    async def detect_weaknesses(self, state: GameReviewState) -> GameReviewState:
        """Node: Weakness Detection."""
        logger.info(f"Detecting weaknesses for game {state['game_id']}")
        state["current_step"] = "weakness_detection"
        state["progress_percentage"] = 95

        try:
            # Detect weaknesses
            weaknesses = await self.weakness_agent.detect_and_persist_weaknesses(
                state["game_id"], state["classifications"]
            )

            state["weaknesses"] = weaknesses
            state["weakness_detection_complete"] = True
            state["progress_percentage"] = 100
            logger.info(f"Weakness detection complete: {len(weaknesses)} weaknesses found")
        except Exception as e:
            logger.error(f"Error detecting weaknesses: {e}")
            state["weakness_error"] = str(e)
            # Don't fail entire review if weakness detection fails
            state["weakness_detection_complete"] = True
            state["weaknesses"] = []

        return state

    def finalize_review(self, state: GameReviewState) -> GameReviewState:
        """Node: Finalize Review."""
        logger.info(f"Finalizing review for game {state['game_id']}")
        state["current_step"] = "complete"
        state["review_complete"] = True
        state["progress_percentage"] = 100

        return state

    def _persist_game(self, state: GameReviewState) -> None:
        """Persist game to database."""
        db = SessionLocal()
        try:
            # Check if game exists
            existing = db.query(Game).filter(Game.game_id == state["game_id"]).first()
            if not existing:
                game = Game(
                    game_id=state["game_id"],
                    pgn=state["pgn"],
                    metadata=state.get("metadata"),
                )
                db.add(game)
                db.commit()
                logger.info(f"Persisted game {state['game_id']}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error persisting game: {e}")
            raise
        finally:
            db.close()

    def should_continue(self, state: GameReviewState) -> str:
        """Conditional edge: Check if workflow should continue."""
        if state.get("review_error"):
            return "end"
        if not state.get("pgn_valid", False):
            return "end"
        return "continue"

    def should_continue_after_validation(self, state: GameReviewState) -> str:
        """Conditional: Continue only if PGN is valid."""
        if state.get("review_error") or not state.get("pgn_valid", False):
            return "finalize_review"
        return "analyze_engine"
    
    def should_continue_after_engine(self, state: GameReviewState) -> str:
        """Conditional: Continue only if engine analysis succeeded."""
        if state.get("review_error") or not state.get("engine_analysis_complete", False):
            return "finalize_review"
        return "classify_moves"
    
    def should_continue_after_classification(self, state: GameReviewState) -> str:
        """Conditional: Continue only if classification succeeded."""
        if state.get("review_error") or not state.get("classification_complete", False):
            return "finalize_review"
        return "generate_explanations"

    def build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(GameReviewState)

        # Add nodes
        workflow.add_node("validate_pgn", self.validate_pgn)
        workflow.add_node("analyze_engine", self.analyze_engine)
        workflow.add_node("classify_moves", self.classify_moves)
        workflow.add_node("generate_explanations", self.generate_explanations)
        workflow.add_node("calculate_accuracy_rating", self.calculate_accuracy_rating)
        workflow.add_node("detect_weaknesses", self.detect_weaknesses)
        workflow.add_node("finalize_review", self.finalize_review)

        # Set entry point
        workflow.add_edge(START, "validate_pgn")

        # Add conditional edges
        workflow.add_conditional_edges(
            "validate_pgn",
            self.should_continue_after_validation,
            {
                "analyze_engine": "analyze_engine",
                "finalize_review": "finalize_review",
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_engine",
            self.should_continue_after_engine,
            {
                "classify_moves": "classify_moves",
                "finalize_review": "finalize_review",
            }
        )
        
        workflow.add_conditional_edges(
            "classify_moves",
            self.should_continue_after_classification,
            {
                "generate_explanations": "generate_explanations",
                "finalize_review": "finalize_review",
            }
        )

        # Add direct edges for remaining steps
        workflow.add_edge("generate_explanations", "calculate_accuracy_rating")
        workflow.add_edge("calculate_accuracy_rating", "detect_weaknesses")
        workflow.add_edge("detect_weaknesses", "finalize_review")
        workflow.add_edge("finalize_review", END)

        return workflow

    async def review_game(
        self, input_data: GameReviewInput
    ) -> GameReviewOutput:
        """
        Execute complete game review workflow.

        Args:
            input_data: Game review input

        Returns:
            Complete game review output
        """
        # Create initial state
        state = self._create_initial_state(
            input_data.pgn, input_data.metadata, input_data.game_id
        )

        # Build and compile graph
        graph = self.build_graph()
        app = graph.compile()

        # Execute workflow
        try:
            final_state = await app.ainvoke(state)

            # Convert to output format
            return GameReviewOutput(
                game_id=final_state["game_id"],
                pgn=final_state["pgn"],
                metadata=final_state.get("metadata"),
                engine_analyses=final_state.get("engine_analyses", []),
                classifications=final_state.get("classifications", []),
                explanations=final_state.get("explanations", {}),
                accuracy=final_state.get("accuracy"),
                estimated_rating=final_state.get("estimated_rating"),
                rating_confidence=final_state.get("rating_confidence"),
                weaknesses=final_state.get("weaknesses", []),
                status="complete" if final_state.get("review_complete") else "error",
                error=final_state.get("review_error"),
            )
        except Exception as e:
            logger.error(f"Error in game review workflow: {e}")
            return GameReviewOutput(
                game_id=state["game_id"],
                pgn=state["pgn"],
                metadata=state.get("metadata"),
                engine_analyses=[],
                classifications=[],
                explanations={},
                accuracy=None,
                estimated_rating=None,
                rating_confidence=None,
                weaknesses=[],
                status="error",
                error=str(e),
            )
