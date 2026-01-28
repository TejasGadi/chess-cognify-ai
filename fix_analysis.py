import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.services.engine_analysis_service import EngineAnalysisService
from app.services.move_classification_service import MoveClassificationService
from app.models.base import SessionLocal
from app.models.game import Game

async def fix_game_analysis():
    game_id = "d63ce811-36c7-447b-9cf6-0cb09ae5dd17"
    print(f"Fixing analysis for game {game_id}...")
    
    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.game_id == game_id).first()
        if not game:
            print("Game not found!")
            return

        pgn = game.pgn
        
        # 1. Run Stockfish Analysis
        print("Running Stockfish analysis...")
        engine_service = EngineAnalysisService()
        analyses = await engine_service.analyze_game(pgn, game_id, use_cache=False)
        print(f"Analyzed {len(analyses)} moves.")
        
        # 2. Persist Analysis
        print("Persisting engine analysis...")
        await engine_service.persist_analysis(game_id, analyses)
        
        # 3. Run Classification
        print("Running move classification...")
        classification_service = MoveClassificationService()
        classifications = classification_service.classify_game_moves(game_id) # fetches from DB
        
        # 4. Persist Classification
        print(f"Persisting {len(classifications)} classifications...")
        classification_service.persist_classifications(game_id, classifications)
        
        print("DONE! Analysis fixed and saved.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_game_analysis())
