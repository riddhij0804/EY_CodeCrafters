"""
Quick test script for Vertex AI Intent Detection integration.

This script tests the intent detector with various message types and
verifies the integration with the sales agent.

Usage:
    python test_vertex_integration.py
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from vertex_intent_detector import detect_intent, get_intent_detector


# Test cases covering different intent types and entity combinations
TEST_CASES = [
    {
        "message": "I need running shoes under 3000",
        "expected_intent": "recommendation",
        "expected_entities": ["category", "price_max"],
        "description": "Basic product search with budget"
    },
    {
        "message": "Looking for a birthday gift for my mom under 5000",
        "expected_intent": "gifting",
        "expected_entities": ["occasion", "recipient_relation", "gender", "price_max"],
        "description": "Gift shopping with recipient details"
    },
    {
        "message": "Is SKU12345 available in my size?",
        "expected_intent": "inventory",
        "expected_entities": ["sku"],
        "description": "Stock availability check"
    },
    {
        "message": "I want to checkout and pay",
        "expected_intent": "payment",
        "expected_entities": [],
        "description": "Purchase intent"
    },
    {
        "message": "What are the trending sneakers right now?",
        "expected_intent": "trend",
        "expected_entities": ["subcategory"],
        "description": "Trend inquiry"
    },
    {
        "message": "Compare Nike Air Max vs Adidas Ultraboost",
        "expected_intent": "comparison",
        "expected_entities": ["brand"],
        "description": "Product comparison"
    },
    {
        "message": "Show me formal shoes for office wear",
        "expected_intent": "recommendation",
        "expected_entities": ["category", "style_preference", "occasion"],
        "description": "Style-specific search"
    },
    {
        "message": "My customer ID is 123456",
        "expected_intent": "fallback",
        "expected_entities": ["customer_id"],
        "description": "Customer identification"
    },
]


async def test_single_message(test_case: dict, detector) -> dict:
    """
    Test a single message and return results.
    
    Args:
        test_case: Test case dictionary
        detector: VertexIntentDetector instance
        
    Returns:
        Test result dictionary
    """
    message = test_case["message"]
    expected_intent = test_case["expected_intent"]
    expected_entities = test_case["expected_entities"]
    
    print(f"\n{'='*80}")
    print(f"TEST: {test_case['description']}")
    print(f"{'='*80}")
    print(f"Message: \"{message}\"")
    print(f"Expected Intent: {expected_intent}")
    print(f"Expected Entities: {', '.join(expected_entities) if expected_entities else 'None'}")
    
    try:
        # Detect intent
        result = await detector.detect_intent(message)
        
        # Display results
        print(f"\n✓ Detection Method: {result['method']}")
        print(f"✓ Detected Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"✓ Extracted Entities: {json.dumps(result['entities'], indent=2)}")
        
        if result.get('reasoning'):
            print(f"✓ Reasoning: {result['reasoning']}")
        
        # Validate results
        intent_match = result['intent'] == expected_intent
        entities_found = all(
            entity in result['entities'] 
            for entity in expected_entities
        )
        
        status = "✅ PASS" if (intent_match and entities_found) else "⚠️ PARTIAL"
        if not intent_match:
            status = "❌ FAIL"
        
        print(f"\n{status}")
        
        if not intent_match:
            print(f"  ⚠ Intent mismatch: expected '{expected_intent}', got '{result['intent']}'")
        
        if not entities_found:
            missing = [e for e in expected_entities if e not in result['entities']]
            print(f"  ⚠ Missing entities: {', '.join(missing)}")
        
        return {
            "test": test_case['description'],
            "status": status,
            "intent_match": intent_match,
            "entities_found": entities_found,
            "method": result['method'],
            "confidence": result['confidence']
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "test": test_case['description'],
            "status": "❌ ERROR",
            "error": str(e),
            "method": "error",
            "confidence": 0.0
        }


async def run_all_tests():
    """Run all test cases and display summary."""
    import json
    
    print("\n" + "="*80)
    print("VERTEX AI INTENT DETECTION - INTEGRATION TEST")
    print("="*80)
    
    # Initialize detector
    print("\nInitializing Vertex AI detector...")
    detector = get_intent_detector()
    
    if detector._initialized:
        print(f"✅ Vertex AI initialized successfully!")
        print(f"   Project: {detector.project_id}")
        print(f"   Region: {detector.location}")
        print(f"   Model: {detector.model_name}")
    else:
        print("⚠️  Vertex AI not available - will use rule-based fallback")
        print("   Set VERTEX_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS to enable Vertex AI")
    
    # Run all tests
    results = []
    for test_case in TEST_CASES:
        result = await test_single_message(test_case, detector)
        results.append(result)
        await asyncio.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for r in results if r['status'] == "✅ PASS")
    partial = sum(1 for r in results if r['status'] == "⚠️ PARTIAL")
    failed = sum(1 for r in results if r['status'] in ["❌ FAIL", "❌ ERROR"])
    
    vertex_used = sum(1 for r in results if r.get('method') == 'vertex_ai')
    rule_based = sum(1 for r in results if r.get('method') == 'rule_based')
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Partial: {partial}")
    print(f"❌ Failed: {failed}")
    print(f"\nDetection Methods:")
    print(f"  Vertex AI: {vertex_used}")
    print(f"  Rule-based: {rule_based}")
    
    if vertex_used > 0:
        avg_confidence = sum(r['confidence'] for r in results if r.get('confidence')) / vertex_used
        print(f"  Average Confidence: {avg_confidence:.2f}")
    
    # Overall status
    print("\n" + "="*80)
    if failed == 0 and partial == 0:
        print("🎉 ALL TESTS PASSED!")
    elif failed == 0:
        print("✅ TESTS COMPLETED WITH PARTIAL MATCHES")
    else:
        print("⚠️  SOME TESTS FAILED - Review errors above")
    print("="*80 + "\n")


async def interactive_test():
    """Interactive testing mode - input your own messages."""
    import json
    
    print("\n" + "="*80)
    print("INTERACTIVE INTENT DETECTION TEST")
    print("="*80)
    print("\nEnter messages to test intent detection.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    detector = get_intent_detector()
    
    while True:
        try:
            message = input("Your message: ").strip()
            
            if message.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye! 👋\n")
                break
            
            if not message:
                continue
            
            print("\nDetecting intent...")
            result = await detector.detect_intent(message)
            
            print(f"\n{'─'*60}")
            print(f"Intent: {result['intent']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Method: {result['method']}")
            print(f"\nEntities:")
            print(json.dumps(result['entities'], indent=2))
            
            if result.get('reasoning'):
                print(f"\nReasoning: {result['reasoning']}")
            
            print(f"{'─'*60}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋\n")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        await interactive_test()
    else:
        await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
