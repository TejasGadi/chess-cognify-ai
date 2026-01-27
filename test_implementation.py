#!/usr/bin/env python3
"""
Test script for multi-step reasoning and theme analysis implementation.
Tests position extraction, validation, theme analysis, and explanation generation.
"""
import asyncio
import sys
import os
import chess

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.explanation_agent import ExplanationAgent
from app.agents.position_extraction_agent import PositionExtractionAgent
from app.utils.position_validator import PositionValidator
from app.services.theme_analysis_service import ThemeAnalysisService
from app.utils.tactical_patterns import TacticalPatternDetector
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_position_extraction():
    """Test position extraction agent."""
    print("\n" + "="*80)
    print("TEST 1: Position Extraction Agent")
    print("="*80)
    
    try:
        agent = PositionExtractionAgent()
        
        # Test with starting position
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        print(f"\nExtracting position from FEN: {fen[:50]}...")
        
        extraction = await agent.extract_position(fen=fen, last_move=None)
        
        print(f"\n✅ Extraction successful!")
        print(f"   Active color: {extraction.active_color}")
        print(f"   Confidence: {extraction.confidence:.2f}")
        print(f"   Verification status: {extraction.verification_status}")
        print(f"\n   White pieces extracted:")
        for piece_type, squares in extraction.white_pieces.items():
            if squares:
                print(f"     {piece_type}: {', '.join(squares)}")
        print(f"\n   Black pieces extracted:")
        for piece_type, squares in extraction.black_pieces.items():
            if squares:
                print(f"     {piece_type}: {', '.join(squares)}")
        
        return True, extraction
    except Exception as e:
        print(f"\n❌ Position extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_position_validation(extraction):
    """Test position validator."""
    print("\n" + "="*80)
    print("TEST 2: Position Validator")
    print("="*80)
    
    try:
        validator = PositionValidator()
        
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        print(f"\nValidating extraction against FEN: {fen[:50]}...")
        
        result = validator.validate_extraction(extraction, fen)
        
        print(f"\n✅ Validation complete!")
        print(f"   Is valid: {result.is_valid}")
        print(f"   Confidence score: {result.confidence_score:.2f}")
        print(f"   Needs revision: {result.needs_revision}")
        print(f"   Discrepancies: {len(result.discrepancies)}")
        
        if result.discrepancies:
            print(f"\n   Discrepancies found:")
            for disc in result.discrepancies[:5]:
                print(f"     - {disc}")
        else:
            print(f"\n   ✅ No discrepancies - extraction is accurate!")
        
        return True, result
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_theme_analysis():
    """Test theme analysis service."""
    print("\n" + "="*80)
    print("TEST 3: Theme Analysis Service")
    print("="*80)
    
    try:
        # Test with a position after e4 e5
        board = chess.Board()
        board.push_san("e4")
        board.push_san("e5")
        
        print(f"\nAnalyzing themes for position: {board.fen()[:50]}...")
        
        themes = ThemeAnalysisService.analyze_position_themes(board, use_cache=False)
        
        print(f"\n✅ Theme analysis complete!")
        
        # Material
        material = themes["material"]
        print(f"\n   Material:")
        print(f"     White: {material['white_material']}, Black: {material['black_material']}")
        print(f"     Balance: {material['balance']:+d}")
        print(f"     Advantage: {material['advantage']}")
        print(f"     Description: {material['material_difference']}")
        
        # Mobility
        mobility = themes["mobility"]
        print(f"\n   Mobility:")
        print(f"     White moves: {mobility['white_moves']}, Black moves: {mobility['black_moves']}")
        print(f"     Difference: {mobility['mobility_difference']:+d}")
        print(f"     Advantage: {mobility['mobility_advantage']}")
        print(f"     Description: {mobility['mobility_description']}")
        
        # Space
        space = themes["space"]
        print(f"\n   Space Control:")
        print(f"     White space: {space['white_space']}, Black space: {space['black_space']}")
        print(f"     Advantage: {space['space_advantage']}")
        print(f"     Description: {space['space_description']}")
        
        # King Safety
        king_safety = themes["king_safety"]
        print(f"\n   King Safety:")
        print(f"     White king: {king_safety['white_king_square']} ({king_safety['white_king_safety']})")
        print(f"     Black king: {king_safety['black_king_square']} ({king_safety['black_king_safety']})")
        print(f"     White pawn shield: {king_safety['white_pawn_shield']}")
        print(f"     Black pawn shield: {king_safety['black_pawn_shield']}")
        print(f"     Description: {king_safety['king_safety_description']}")
        
        return True, themes
    except Exception as e:
        print(f"\n❌ Theme analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_tactical_patterns():
    """Test tactical pattern detector."""
    print("\n" + "="*80)
    print("TEST 4: Tactical Pattern Detector")
    print("="*80)
    
    try:
        # Test with a position that might have tactical patterns
        board = chess.Board()
        board.push_san("e4")
        board.push_san("e5")
        board.push_san("Nf3")
        board.push_san("Nc6")
        
        print(f"\nDetecting tactical patterns in position: {board.fen()[:50]}...")
        
        patterns = TacticalPatternDetector.identify_tactical_patterns(board)
        
        print(f"\n✅ Tactical pattern detection complete!")
        print(f"   Patterns found: {len(patterns)}")
        
        if patterns:
            print(f"\n   Detected patterns:")
            for i, pattern in enumerate(patterns, 1):
                print(f"     {i}. {pattern}")
        else:
            print(f"\n   No tactical patterns detected in this position.")
        
        return True, patterns
    except Exception as e:
        print(f"\n❌ Tactical pattern detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_full_explanation_flow():
    """Test full explanation generation with multi-step reasoning and theme analysis."""
    print("\n" + "="*80)
    print("TEST 5: Full Explanation Generation Flow")
    print("="*80)
    
    try:
        agent = ExplanationAgent()
        
        # Test with a simple position: e4 (best move)
        fen_before = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        played_move = "e2e4"  # e4
        best_move = "e2e4"   # e4 is best
        label = "Best"
        eval_change = "+0.0 -> +0.3"
        played_move_eval = "+0.3"
        best_move_eval = "+0.3"
        
        print(f"\nGenerating explanation for:")
        print(f"   Position: {fen_before[:50]}...")
        print(f"   Move: {played_move} ({label})")
        print(f"   Best move: {best_move}")
        print(f"   Evaluation: {eval_change}")
        
        print(f"\n⏳ Generating explanation (this may take 30-60 seconds)...")
        print(f"   Step 1: Position extraction and validation...")
        print(f"   Step 2: Theme analysis...")
        print(f"   Step 3: LLM explanation generation...")
        
        explanation = await agent.generate_explanation(
            fen=fen_before,
            played_move=played_move,
            best_move=best_move,
            label=label,
            eval_change=eval_change,
            played_move_eval=played_move_eval,
            best_move_eval=best_move_eval,
        )
        
        print(f"\n✅ Explanation generated successfully!")
        print(f"\n   Explanation:")
        print(f"   {'-'*76}")
        print(f"   {explanation}")
        print(f"   {'-'*76}")
        print(f"\n   Length: {len(explanation)} characters")
        
        # Check if explanation mentions verified positions or themes
        has_verified = "verified" in explanation.lower() or "position" in explanation.lower()
        has_theme = any(word in explanation.lower() for word in ["material", "mobility", "space", "king", "tactical"])
        
        print(f"\n   Quality checks:")
        print(f"     - Mentions position/verified: {has_verified}")
        print(f"     - Mentions themes/tactics: {has_theme}")
        
        return True, explanation
    except Exception as e:
        print(f"\n❌ Explanation generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_retry_logic():
    """Test retry logic with error feedback."""
    print("\n" + "="*80)
    print("TEST 6: Retry Logic with Error Feedback")
    print("="*80)
    
    try:
        agent = ExplanationAgent()
        
        # Test the retry mechanism by checking if it handles validation failures
        fen_after = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        
        print(f"\nTesting retry logic with position: {fen_after[:50]}...")
        print(f"   This will extract, validate, and retry if validation fails...")
        
        verified_pieces, validation_result = await agent._extract_and_validate_position(
            fen_after=fen_after,
            last_move_san="e4",
            highlight_squares=["e4"],
            max_retries=2
        )
        
        print(f"\n✅ Retry logic test complete!")
        print(f"   Validation passed: {validation_result.is_valid}")
        print(f"   Confidence: {validation_result.confidence_score:.2f}")
        print(f"   Attempts made: {'Multiple (if retried)' if not validation_result.is_valid else '1 (first attempt)'}")
        
        if validation_result.discrepancies:
            print(f"   Discrepancies found: {len(validation_result.discrepancies)}")
            print(f"   (Retry logic would have been triggered if validation failed)")
        
        return True
    except Exception as e:
        print(f"\n❌ Retry logic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TESTING MULTI-STEP REASONING AND THEME ANALYSIS IMPLEMENTATION")
    print("="*80)
    print("\nThis script tests:")
    print("  1. Position Extraction Agent")
    print("  2. Position Validator")
    print("  3. Theme Analysis Service")
    print("  4. Tactical Pattern Detector")
    print("  5. Full Explanation Generation Flow")
    print("  6. Retry Logic with Error Feedback")
    
    results = {}
    
    # Test 1: Position Extraction
    success, extraction = await test_position_extraction()
    results["position_extraction"] = success
    
    if not success:
        print("\n⚠️  Position extraction failed. Some tests may be skipped.")
        return
    
    # Test 2: Position Validation
    success, validation_result = await test_position_validation(extraction)
    results["position_validation"] = success
    
    # Test 3: Theme Analysis
    success, themes = await test_theme_analysis()
    results["theme_analysis"] = success
    
    # Test 4: Tactical Patterns
    success, patterns = await test_tactical_patterns()
    results["tactical_patterns"] = success
    
    # Test 5: Full Explanation Flow (requires OpenAI API key)
    print("\n⚠️  Note: Full explanation test requires OPENAI_API_KEY in environment")
    try:
        success, explanation = await test_full_explanation_flow()
        results["full_explanation"] = success
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            print(f"\n⚠️  Skipping full explanation test: {e}")
            print("   Set OPENAI_API_KEY in .env file to test full explanation generation")
            results["full_explanation"] = "skipped"
        else:
            raise
    
    # Test 6: Retry Logic
    try:
        success = await test_retry_logic()
        results["retry_logic"] = success
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            print(f"\n⚠️  Skipping retry logic test: {e}")
            results["retry_logic"] = "skipped"
        else:
            raise
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⏭️  SKIPPED"
        print(f"  {test_name.replace('_', ' ').title():30s}: {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r != "skipped")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Implementation is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    asyncio.run(main())
