
import asyncio
import logging
import sys
import os

# Ensure app can be imported
sys.path.append(os.getcwd())

from app.agents.explanation_agent import ExplanationAgent
from app.models.base import SessionLocal
from app.models.game import Game, MoveReview
from app.utils.logger import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

async def fix_explanations(game_id: str):
    print(f"Checking explanations for game {game_id}...")
    
    db = SessionLocal()
    try:
        # Check for missing explanations
        reviews = db.query(MoveReview).filter(
            MoveReview.game_id == game_id
        ).order_by(MoveReview.ply).all()
        
        missing_count = 0
        total_count = len(reviews)
        
        print(f"Found {total_count} move reviews.")
        
        for review in reviews:
            if not review.explanation:
                missing_count += 1
                print(f"  Ply {review.ply}: Missing explanation")
        
        print(f"Total missing: {missing_count}/{total_count}")
        
        if missing_count > 0:
            print("Triggering explanation generation...")
            agent = ExplanationAgent()
            # Force cache=False to ensure we retry failed ones (though missing ones are effectively uncached)
            # using use_cache=True because we only want to fill in the missing ones, 
            # and the agent logic naturally skips existing ones if use_cache=True.
            # However, if they were "generated" but empty/null, we want to retry.
            # The agent's explain_game_moves logic: "if use_cache and move_review.explanation: ... else: moves_to_generate.append"
            # So use_cache=True is correct to fill gaps.
            
            explanations = await agent.explain_game_moves(game_id, use_cache=True)
            print(f"Generation complete. Result count: {len(explanations)}")
            
            # Re-check db
            db.expire_all()
            missing_after = db.query(MoveReview).filter(
                MoveReview.game_id == game_id,
                MoveReview.explanation == None
            ).count()
            print(f"Missing after generation: {missing_after}")
        else:
            print("No missing explanations found.")
            
    finally:
        db.close()

if __name__ == "__main__":
    # The game ID observed in logs with rate limit errors
    GAME_ID = "259ceb8b-2473-4f8d-94af-dc1c06a4081a"
    
    # Also check the previous game just in case
    # GAME_ID = "d63ce811-36c7-447b-9cf6-0cb09ae5dd17" 
    
    if len(sys.argv) > 1:
        GAME_ID = sys.argv[1]
        
    asyncio.run(fix_explanations(GAME_ID))
