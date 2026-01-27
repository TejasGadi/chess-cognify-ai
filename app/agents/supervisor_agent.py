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
        logger.debug("Initializing SupervisorAgent")
        self.pgn_service = PGNService()
        self.engine_service = EngineAnalysisService()
        self.classification_service = MoveClassificationService()
        self.accuracy_service = AccuracyRatingService()
        self.explanation_agent = ExplanationAgent()
        self.weakness_agent = WeaknessDetectionAgent()
        logger.info("SupervisorAgent initialized with all services")

    def _create_initial_state(
        self, pgn: str, metadata: Optional[Dict[str, Any]] = None, game_id: Optional[str] = None
    ) -> GameReviewState:
        """Create initial state for workflow."""
        if game_id is None:
            game_id = str(uuid.uuid4())
            logger.debug(f"Generated new game_id: {game_id}")
        else:
            logger.debug(f"Using provided game_id: {game_id}")

        logger.info(f"Creating initial state for game {game_id}")
        logger.debug(f"PGN length: {len(pgn)} characters, metadata keys: {list(metadata.keys()) if metadata else []}")

        state = {
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
        
        logger.debug(f"Initial state created: game_id={game_id}, step={state['current_step']}, progress={state['progress_percentage']}%")
        return state

    async def validate_pgn(self, state: GameReviewState) -> GameReviewState:
        """Node: Validate PGN."""
        if state is None:
            logger.error("[WORKFLOW] Node: validate_pgn - Received None state")
            raise ValueError("State is None in validate_pgn node")
        
        game_id = state.get('game_id')
        if not game_id:
            logger.error("[WORKFLOW] Node: validate_pgn - game_id is missing from state")
            raise ValueError("game_id is missing from state")
        
        logger.info(f"[WORKFLOW] Node: validate_pgn - Starting for game {game_id}")
        logger.debug(f"[WORKFLOW] State before validate_pgn: step={state.get('current_step')}, progress={state.get('progress_percentage')}%")
        
        state["current_step"] = "validating_pgn"
        state["progress_percentage"] = 5

        try:
            logger.debug(f"[WORKFLOW] Calling PGNService.validate_pgn()")
            is_valid, error = self.pgn_service.validate_pgn(state["pgn"])
            state["pgn_valid"] = is_valid
            state["validation_error"] = error

            if not is_valid:
                state["review_error"] = f"PGN validation failed: {error}"
                state["review_complete"] = True
                logger.error(f"[WORKFLOW] Node: validate_pgn - FAILED: {error}")
                logger.debug(f"[WORKFLOW] State after validate_pgn: pgn_valid=False, review_complete=True")
            else:
                logger.info(f"[WORKFLOW] Node: validate_pgn - SUCCESS: PGN is valid")
                logger.debug(f"[WORKFLOW] State after validate_pgn: pgn_valid=True, validation_error=None")
        except Exception as e:
            logger.error(f"[WORKFLOW] Node: validate_pgn - EXCEPTION: {e}", exc_info=True)
            state["pgn_valid"] = False
            state["validation_error"] = str(e)
            state["review_error"] = f"PGN validation error: {e}"
            state["review_complete"] = True
            logger.debug(f"[WORKFLOW] State after validate_pgn exception: pgn_valid=False, review_complete=True")

        logger.debug(f"[WORKFLOW] Node: validate_pgn - Completed, returning state")
        return state

    async def analyze_engine(self, state: GameReviewState) -> GameReviewState:
        """Node: Engine Analysis."""
        if state is None:
            logger.error("[WORKFLOW] Node: analyze_engine - Received None state")
            raise ValueError("State is None in analyze_engine node")
        
        game_id = state.get('game_id')
        if not game_id:
            logger.error("[WORKFLOW] Node: analyze_engine - game_id is missing from state")
            raise ValueError("game_id is missing from state")
        
        logger.info(f"[WORKFLOW] Node: analyze_engine - Starting for game {game_id}")
        logger.debug(f"[WORKFLOW] State before analyze_engine: step={state.get('current_step')}, progress={state.get('progress_percentage')}%")
        
        state["current_step"] = "engine_analysis"
        state["progress_percentage"] = 20

        try:
            # Persist game first
            logger.debug(f"[WORKFLOW] Persisting game to database")
            self._persist_game(state)

            # Analyze game
            logger.debug(f"[WORKFLOW] Calling EngineAnalysisService.analyze_game()")
            logger.info(f"[AGENT] EngineAnalysisService - Starting analysis for game {game_id}")
            analyses = await self.engine_service.analyze_game(
                state["pgn"], state["game_id"], use_cache=True
            )

            if not analyses or len(analyses) == 0:
                error_msg = "Engine analysis returned no results - check Stockfish configuration"
                logger.error(f"[WORKFLOW] Node: analyze_engine - FAILED: {error_msg}")
                raise ValueError(error_msg)

            logger.debug(f"[WORKFLOW] Engine analysis returned {len(analyses)} move analyses")
            logger.info(f"[AGENT] EngineAnalysisService - Completed: {len(analyses)} moves analyzed")

            # Persist analyses
            logger.debug(f"[WORKFLOW] Persisting engine analyses to database")
            await self.engine_service.persist_analysis(state["game_id"], analyses)

            state["engine_analyses"] = analyses
            state["engine_analysis_complete"] = True
            state["progress_percentage"] = 40
            
            # Log agent output
            logger.info(f"[WORKFLOW] Node: analyze_engine - OUTPUT: {len(analyses)} moves analyzed")
            if analyses:
                # Sample analysis outputs
                sample_analyses = analyses[:3]
                for analysis in sample_analyses:
                    logger.debug(f"[WORKFLOW] Node: analyze_engine - Sample (ply {analysis.get('ply')}): {analysis.get('played_move')} -> eval: {analysis.get('eval_after')}, best: {analysis.get('best_move')}")
                # Summary stats
                depths_used = [a.get('analysis_depth', 'default') for a in analyses]
                depth_counts = {}
                for depth in depths_used:
                    depth_counts[depth] = depth_counts.get(depth, 0) + 1
                logger.info(f"[WORKFLOW] Node: analyze_engine - Analysis depth breakdown: {depth_counts}")
            
            logger.info(f"[WORKFLOW] Node: analyze_engine - SUCCESS: {len(analyses)} moves analyzed")
            logger.debug(f"[WORKFLOW] State after analyze_engine: engine_analysis_complete=True, progress=40%")
        except Exception as e:
            logger.error(f"[WORKFLOW] Node: analyze_engine - EXCEPTION: {e}", exc_info=True)
            state["engine_analysis_error"] = str(e)
            state["engine_analysis_complete"] = False
            state["review_error"] = f"Engine analysis error: {e}"
            state["review_complete"] = True
            logger.debug(f"[WORKFLOW] State after analyze_engine exception: engine_analysis_complete=False, review_complete=True")

        logger.debug(f"[WORKFLOW] Node: analyze_engine - Completed, returning state")
        return state

    async def classify_moves(self, state: GameReviewState) -> GameReviewState:
        """Node: Move Classification."""
        if state is None:
            logger.error("[WORKFLOW] Node: classify_moves - Received None state")
            raise ValueError("State is None in classify_moves node")
        
        game_id = state.get('game_id')
        if not game_id:
            logger.error("[WORKFLOW] Node: classify_moves - game_id is missing from state")
            raise ValueError("game_id is missing from state")
        
        logger.info(f"[WORKFLOW] Node: classify_moves - Starting for game {game_id}")
        logger.debug(f"[WORKFLOW] State before classify_moves: step={state.get('current_step')}, progress={state.get('progress_percentage')}%")
        
        state["current_step"] = "move_classification"
        state["progress_percentage"] = 50

        try:
            engine_analyses = state.get("engine_analyses", [])
            if not engine_analyses or len(engine_analyses) == 0:
                error_msg = "No engine analyses available for classification"
                logger.error(f"[WORKFLOW] Node: classify_moves - FAILED: {error_msg}")
                raise ValueError(error_msg)

            logger.debug(f"[WORKFLOW] Classifying {len(engine_analyses)} moves")
            logger.info(f"[AGENT] MoveClassificationService - Starting classification for game {game_id}")

            # Classify moves
            classifications = self.classification_service.classify_game_moves(
                state["game_id"], engine_analyses
            )

            if not classifications or len(classifications) == 0:
                error_msg = "Move classification returned no results"
                logger.error(f"[WORKFLOW] Node: classify_moves - FAILED: {error_msg}")
                raise ValueError(error_msg)

            logger.debug(f"[WORKFLOW] Classification returned {len(classifications)} results")
            logger.info(f"[AGENT] MoveClassificationService - Completed: {len(classifications)} moves classified")

            # Add phases
            logger.debug(f"[WORKFLOW] Adding game phases to classifications")
            classifications = self.classification_service.add_game_phases(
                state["game_id"], classifications, state["pgn"]
            )

            # Persist classifications
            logger.debug(f"[WORKFLOW] Persisting classifications to database")
            self.classification_service.persist_classifications(
                state["game_id"], classifications
            )

            state["classifications"] = classifications
            state["classification_complete"] = True
            state["progress_percentage"] = 60
            
            # Log agent output
            logger.info(f"[WORKFLOW] Node: classify_moves - OUTPUT: {len(classifications)} moves classified")
            if classifications:
                # Count by label
                label_counts = {}
                for cls in classifications:
                    label = cls.get("label", "Unknown")
                    label_counts[label] = label_counts.get(label, 0) + 1
                logger.info(f"[WORKFLOW] Node: classify_moves - Classification breakdown: {label_counts}")
                # Sample classifications
                sample_classifications = classifications[:5]
                for cls in sample_classifications:
                    logger.debug(f"[WORKFLOW] Node: classify_moves - Sample (ply {cls.get('ply')}): {cls.get('label')} - {cls.get('centipawn_loss', 'N/A')} cp loss")
            
            logger.info(f"[WORKFLOW] Node: classify_moves - SUCCESS: {len(classifications)} moves classified")
            logger.debug(f"[WORKFLOW] State after classify_moves: classification_complete=True, progress=60%")
        except Exception as e:
            logger.error(f"[WORKFLOW] Node: classify_moves - EXCEPTION: {e}", exc_info=True)
            state["classification_error"] = str(e)
            state["classification_complete"] = False
            state["review_error"] = f"Move classification error: {e}"
            state["review_complete"] = True
            logger.debug(f"[WORKFLOW] State after classify_moves exception: classification_complete=False, review_complete=True")

        logger.debug(f"[WORKFLOW] Node: classify_moves - Completed, returning state")
        return state

    async def generate_explanations(self, state: GameReviewState) -> GameReviewState:
        """Node: Generate Explanations (conditional)."""
        if state is None:
            logger.error("[WORKFLOW] Node: generate_explanations - Received None state")
            raise ValueError("State is None in generate_explanations node")
        
        game_id = state.get('game_id')
        if not game_id:
            logger.error("[WORKFLOW] Node: generate_explanations - game_id is missing from state")
            raise ValueError("game_id is missing from state")
        
        logger.info(f"[WORKFLOW] Node: generate_explanations - Starting for game {game_id}")
        logger.debug(f"[WORKFLOW] State before generate_explanations: step={state.get('current_step')}, progress={state.get('progress_percentage')}%")
        
        state["current_step"] = "generating_explanations"
        state["progress_percentage"] = 70

        try:
            # Generate explanations for mistakes
            logger.debug(f"[WORKFLOW] Calling ExplanationAgent.explain_game_moves()")
            logger.info(f"[AGENT] ExplanationAgent - Starting explanation generation for game {game_id}")
            explanations = await self.explanation_agent.explain_game_moves(
                state["game_id"], use_cache=True
            )

            state["explanations"] = explanations
            state["explanation_complete"] = True
            state["progress_percentage"] = 75
            logger.info(f"[WORKFLOW] Node: generate_explanations - SUCCESS: {len(explanations)} explanations generated")
            logger.info(f"[AGENT] ExplanationAgent - Completed: {len(explanations)} explanations generated")
            
            # Log agent output details
            logger.info(f"[WORKFLOW] Node: generate_explanations - OUTPUT: {len(explanations)} explanations")
            if explanations:
                sample_plies = sorted(list(explanations.keys()))[:5]
                for ply in sample_plies:
                    logger.info(f"[WORKFLOW] Node: generate_explanations - Sample output (ply {ply}): {explanations[ply][:150]}...")
            
            logger.debug(f"[WORKFLOW] State after generate_explanations: explanation_complete=True, progress=75%")
        except Exception as e:
            logger.error(f"[WORKFLOW] Node: generate_explanations - EXCEPTION: {e}", exc_info=True)
            logger.error(f"[AGENT] ExplanationAgent - Error: {e}")
            state["explanation_error"] = str(e)
            # Don't fail entire review if explanations fail
            state["explanation_complete"] = True
            state["explanations"] = {}
            logger.debug(f"[WORKFLOW] State after generate_explanations exception: explanation_complete=True (non-fatal), explanations={{}}")

        logger.debug(f"[WORKFLOW] Node: generate_explanations - Completed, returning state")
        return state

    async def calculate_accuracy_rating(self, state: GameReviewState) -> GameReviewState:
        """Node: Accuracy & Rating."""
        if state is None:
            logger.error("[WORKFLOW] Node: calculate_accuracy_rating - Received None state")
            raise ValueError("State is None in calculate_accuracy_rating node")
        
        game_id = state.get('game_id', 'unknown')
        logger.info(f"[WORKFLOW] Node: calculate_accuracy_rating - Starting for game {game_id}")
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
            
            # Log agent output
            logger.info(f"[WORKFLOW] Node: calculate_accuracy_rating - OUTPUT:")
            logger.info(f"[WORKFLOW] Node: calculate_accuracy_rating - Accuracy: {accuracy_metrics['accuracy']}%")
            logger.info(f"[WORKFLOW] Node: calculate_accuracy_rating - Estimated Rating: {rating_info['estimated_rating']}")
            logger.info(f"[WORKFLOW] Node: calculate_accuracy_rating - Rating Confidence: {rating_info['confidence']}")
            logger.info(f"[WORKFLOW] Node: calculate_accuracy_rating - Blunders: {accuracy_metrics.get('blunder_count', 0)}, Mistakes: {accuracy_metrics.get('mistake_count', 0)}, Inaccuracies: {accuracy_metrics.get('inaccuracy_count', 0)}")
            logger.debug(f"[WORKFLOW] Node: calculate_accuracy_rating - Full metrics: {accuracy_metrics}")
            
            logger.info(f"[WORKFLOW] Node: calculate_accuracy_rating - Accuracy and rating complete: {accuracy_metrics['accuracy']}% accuracy")
        except Exception as e:
            logger.error(f"Error calculating accuracy/rating: {e}")
            state["accuracy_error"] = str(e)
            state["accuracy_complete"] = False
            state["review_error"] = f"Accuracy calculation error: {e}"
            state["review_complete"] = True

        return state

    async def detect_weaknesses(self, state: GameReviewState) -> GameReviewState:
        """Node: Weakness Detection."""
        if state is None:
            logger.error("[WORKFLOW] Node: detect_weaknesses - Received None state")
            raise ValueError("State is None in detect_weaknesses node")
        
        game_id = state.get('game_id', 'unknown')
        logger.info(f"[WORKFLOW] Node: detect_weaknesses - Starting for game {game_id}")
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
            
            # Log agent output
            logger.info(f"[WORKFLOW] Node: detect_weaknesses - OUTPUT: {len(weaknesses)} weaknesses detected")
            logger.info(f"[WORKFLOW] Node: detect_weaknesses - Weaknesses: {weaknesses}")
            for i, weakness in enumerate(weaknesses, 1):
                logger.info(f"[WORKFLOW] Node: detect_weaknesses -   {i}. {weakness}")
            
            logger.info(f"[WORKFLOW] Node: detect_weaknesses - Weakness detection complete: {len(weaknesses)} weaknesses found")
        except Exception as e:
            logger.error(f"Error detecting weaknesses: {e}")
            state["weakness_error"] = str(e)
            # Don't fail entire review if weakness detection fails
            state["weakness_detection_complete"] = True
            state["weaknesses"] = []

        return state

    def finalize_review(self, state: GameReviewState) -> GameReviewState:
        """Node: Finalize Review."""
        if state is None:
            logger.error("[WORKFLOW] Node: finalize_review - Received None state")
            raise ValueError("State is None in finalize_review node")
        
        game_id = state.get('game_id', 'unknown')
        logger.info(f"[WORKFLOW] Node: finalize_review - Starting for game {game_id}")
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
        game_id = state.get('game_id', 'unknown')
        has_error = bool(state.get("review_error"))
        pgn_valid = state.get("pgn_valid", False)
        
        if has_error or not pgn_valid:
            decision = "finalize_review"
            logger.debug(f"[WORKFLOW] Conditional edge: should_continue_after_validation -> {decision} (has_error={has_error}, pgn_valid={pgn_valid})")
            return decision
        
        decision = "analyze_engine"
        logger.debug(f"[WORKFLOW] Conditional edge: should_continue_after_validation -> {decision} (PGN valid, proceeding)")
        return decision
    
    def should_continue_after_engine(self, state: GameReviewState) -> str:
        """Conditional: Continue only if engine analysis succeeded."""
        game_id = state.get('game_id', 'unknown')
        has_error = bool(state.get("review_error"))
        engine_complete = state.get("engine_analysis_complete", False)
        
        if has_error or not engine_complete:
            decision = "finalize_review"
            logger.debug(f"[WORKFLOW] Conditional edge: should_continue_after_engine -> {decision} (has_error={has_error}, engine_complete={engine_complete})")
            return decision
        
        decision = "classify_moves"
        logger.debug(f"[WORKFLOW] Conditional edge: should_continue_after_engine -> {decision} (engine analysis complete, proceeding)")
        return decision
    
    def should_continue_after_classification(self, state: GameReviewState) -> str:
        """Conditional: Continue only if classification succeeded."""
        game_id = state.get('game_id', 'unknown')
        has_error = bool(state.get("review_error"))
        classification_complete = state.get("classification_complete", False)
        
        if has_error or not classification_complete:
            decision = "finalize_review"
            logger.debug(f"[WORKFLOW] Conditional edge: should_continue_after_classification -> {decision} (has_error={has_error}, classification_complete={classification_complete})")
            return decision
        
        decision = "generate_explanations"
        logger.debug(f"[WORKFLOW] Conditional edge: should_continue_after_classification -> {decision} (classification complete, proceeding)")
        return decision

    def build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        logger.info("[WORKFLOW] Building LangGraph workflow graph")
        logger.debug("[WORKFLOW] Creating StateGraph with GameReviewState")
        
        workflow = StateGraph(GameReviewState)

        # Add nodes
        logger.debug("[WORKFLOW] Adding workflow nodes")
        workflow.add_node("validate_pgn", self.validate_pgn)
        logger.debug("[WORKFLOW] Added node: validate_pgn")
        workflow.add_node("analyze_engine", self.analyze_engine)
        logger.debug("[WORKFLOW] Added node: analyze_engine")
        workflow.add_node("classify_moves", self.classify_moves)
        logger.debug("[WORKFLOW] Added node: classify_moves")
        workflow.add_node("generate_explanations", self.generate_explanations)
        logger.debug("[WORKFLOW] Added node: generate_explanations")
        workflow.add_node("calculate_accuracy_rating", self.calculate_accuracy_rating)
        logger.debug("[WORKFLOW] Added node: calculate_accuracy_rating")
        workflow.add_node("detect_weaknesses", self.detect_weaknesses)
        logger.debug("[WORKFLOW] Added node: detect_weaknesses")
        workflow.add_node("finalize_review", self.finalize_review)
        logger.debug("[WORKFLOW] Added node: finalize_review")

        # Set entry point
        logger.debug("[WORKFLOW] Setting entry point: START -> validate_pgn")
        workflow.add_edge(START, "validate_pgn")

        # Add conditional edges
        logger.debug("[WORKFLOW] Adding conditional edge: validate_pgn -> (analyze_engine | finalize_review)")
        workflow.add_conditional_edges(
            "validate_pgn",
            self.should_continue_after_validation,
            {
                "analyze_engine": "analyze_engine",
                "finalize_review": "finalize_review",
            }
        )
        
        logger.debug("[WORKFLOW] Adding conditional edge: analyze_engine -> (classify_moves | finalize_review)")
        workflow.add_conditional_edges(
            "analyze_engine",
            self.should_continue_after_engine,
            {
                "classify_moves": "classify_moves",
                "finalize_review": "finalize_review",
            }
        )
        
        logger.debug("[WORKFLOW] Adding conditional edge: classify_moves -> (generate_explanations | finalize_review)")
        workflow.add_conditional_edges(
            "classify_moves",
            self.should_continue_after_classification,
            {
                "generate_explanations": "generate_explanations",
                "finalize_review": "finalize_review",
            }
        )

        # Add direct edges for remaining steps
        logger.debug("[WORKFLOW] Adding direct edges")
        workflow.add_edge("generate_explanations", "calculate_accuracy_rating")
        logger.debug("[WORKFLOW] Added edge: generate_explanations -> calculate_accuracy_rating")
        workflow.add_edge("calculate_accuracy_rating", "detect_weaknesses")
        logger.debug("[WORKFLOW] Added edge: calculate_accuracy_rating -> detect_weaknesses")
        workflow.add_edge("detect_weaknesses", "finalize_review")
        logger.debug("[WORKFLOW] Added edge: detect_weaknesses -> finalize_review")
        workflow.add_edge("finalize_review", END)
        logger.debug("[WORKFLOW] Added edge: finalize_review -> END")

        logger.info("[WORKFLOW] LangGraph workflow graph built successfully")
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
        logger.info("=" * 80)
        logger.info("[WORKFLOW] ========== STARTING GAME REVIEW WORKFLOW ==========")
        logger.info(f"[WORKFLOW] Game ID: {input_data.game_id or 'NEW'}")
        logger.info(f"[WORKFLOW] PGN Length: {len(input_data.pgn)} characters")
        logger.debug(f"[WORKFLOW] Metadata: {input_data.metadata}")
        
        # Create initial state
        logger.debug("[WORKFLOW] Creating initial state")
        state = self._create_initial_state(
            input_data.pgn, input_data.metadata, input_data.game_id
        )
        
        # Check if state is None (shouldn't happen, but safety check)
        if state is None:
            logger.error("[WORKFLOW] _create_initial_state returned None")
            raise ValueError("Failed to create initial state - state is None")
        
        game_id = state.get("game_id")
        if not game_id:
            logger.error("[WORKFLOW] State created but game_id is missing")
            raise ValueError("State created but game_id is missing")
        
        logger.info(f"[WORKFLOW] Initial state created for game {game_id}")

        # Build and compile graph
        logger.debug("[WORKFLOW] Building LangGraph workflow")
        graph = self.build_graph()
        logger.debug("[WORKFLOW] Compiling LangGraph workflow")
        app = graph.compile()
        logger.info("[WORKFLOW] LangGraph workflow compiled and ready for execution")

        # Get Langfuse callback handler for tracing
        from app.utils.langfuse_handler import get_langfuse_handler
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            logger.info("[WORKFLOW] Langfuse tracing enabled for workflow")
        else:
            logger.debug("[WORKFLOW] Langfuse tracing disabled or not configured")
        
        # Execute workflow
        try:
            logger.info(f"[WORKFLOW] ========== EXECUTING WORKFLOW FOR GAME {game_id} ==========")
            logger.debug(f"[WORKFLOW] Invoking workflow with initial state: step={state.get('current_step', 'unknown')}, progress={state.get('progress_percentage', 0)}%")
            
            # LangGraph supports callbacks via config
            config = {}
            if langfuse_handler:
                config["callbacks"] = [langfuse_handler]
            
            final_state = await app.ainvoke(state, config=config)
            
            # Check if final_state is None
            if final_state is None:
                logger.error(f"[WORKFLOW] Workflow returned None state for game {game_id}")
                raise ValueError("Workflow execution returned None state")
            
            logger.info(f"[WORKFLOW] ========== WORKFLOW EXECUTION COMPLETE FOR GAME {game_id} ==========")
            logger.info(f"[WORKFLOW] Final state: step={final_state.get('current_step')}, progress={final_state.get('progress_percentage')}%, review_complete={final_state.get('review_complete')}")
            logger.debug(f"[WORKFLOW] Final state summary:")
            logger.debug(f"[WORKFLOW]   - Engine analyses: {len(final_state.get('engine_analyses', []))}")
            logger.debug(f"[WORKFLOW]   - Classifications: {len(final_state.get('classifications', []))}")
            logger.debug(f"[WORKFLOW]   - Explanations: {len(final_state.get('explanations', {}))}")
            logger.debug(f"[WORKFLOW]   - Accuracy: {final_state.get('accuracy')}")
            logger.debug(f"[WORKFLOW]   - Estimated rating: {final_state.get('estimated_rating')}")
            logger.debug(f"[WORKFLOW]   - Weaknesses: {len(final_state.get('weaknesses', []))}")
            logger.debug(f"[WORKFLOW]   - Status: {'complete' if final_state.get('review_complete') else 'error'}")
            logger.debug(f"[WORKFLOW]   - Error: {final_state.get('review_error')}")

            # Convert to output format
            # Use .get() for all fields to handle missing keys safely
            output = GameReviewOutput(
                game_id=final_state.get("game_id", state.get("game_id", "unknown")),
                pgn=final_state.get("pgn", state.get("pgn", "")),
                metadata=final_state.get("metadata", state.get("metadata")),
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
            
            logger.info(f"[WORKFLOW] ========== WORKFLOW SUCCESSFUL FOR GAME {game_id} ==========")
            logger.info("=" * 80)
            return output
        except Exception as e:
            logger.error(f"[WORKFLOW] ========== WORKFLOW EXCEPTION FOR GAME {game_id} ==========")
            logger.error(f"[WORKFLOW] Error in game review workflow: {e}", exc_info=True)
            logger.error("=" * 80)
            
            # Use .get() to safely access state fields
            output = GameReviewOutput(
                game_id=state.get("game_id", "unknown"),
                pgn=state.get("pgn", ""),
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
            return output