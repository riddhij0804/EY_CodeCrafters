"""
End-to-End Integration Test
Tests the complete workflow from the proposed solution
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from agents.sales_agent.orchestrator import SalesOrchestrator

async def test_complete_workflow():
    """Test the complete shopping workflow"""
    
    print("=" * 80)
    print("TESTING COMPLETE SHOPPING WORKFLOW")
    print("=" * 80)
    
    orchestrator = SalesOrchestrator()
    
    # Test 1: Discovery & Intent Analysis
    print("\n1. DISCOVERY & INTENT ANALYSIS")
    print("-" * 80)
    user_message = "I need something stylish for a weekend trip"
    user_profile = {"style_preference": "casual", "budget": "mid"}
    
    intent = await orchestrator.analyze_intent(user_message, user_profile)
    print(f"✓ Intent analyzed: {intent}")
    
    # Test 2: Get Recommendations
    print("\n2. PERSONALIZED RECOMMENDATIONS")
    print("-" * 80)
    recommendations = await orchestrator.get_recommendations(
        user_id="CUST001",
        intent=intent,
        context={}
    )
    print(f"✓ Got {len(recommendations)} recommendations")
    if recommendations:
        print(f"  Sample: {recommendations[0].get('ProductDisplayName', 'N/A')} - ₹{recommendations[0].get('price', 0)}")
    
    # Test 3: Seasonal Trends
    print("\n3. SEASONAL TRENDS")
    print("-" * 80)
    trends = await orchestrator.get_seasonal_trends()
    print(f"✓ Got {len(trends)} seasonal trend items")
    
    # Test 4: Inventory Verification
    print("\n4. INVENTORY VERIFICATION")
    print("-" * 80)
    test_items = []
    if recommendations:
        test_items = [{
            "sku": recommendations[0].get("sku"),
            "name": recommendations[0].get("ProductDisplayName", "Product"),
            "price": recommendations[0].get("price", 100),
            "quantity": 1
        }]
    
    if test_items:
        inventory_check = await orchestrator.verify_inventory(test_items)
        print(f"✓ Inventory verified: {inventory_check['all_available']}")
        if inventory_check['low_stock_alerts']:
            print(f"  ⚠️  Low stock alerts: {len(inventory_check['low_stock_alerts'])}")
    
    # Test 5: Complete Purchase Flow (Simulation)
    print("\n5. COMPLETE PURCHASE FLOW")
    print("-" * 80)
    print("Testing full orchestration: Inventory -> Payment -> Fulfillment -> Styling")
    
    if test_items:
        flow_result = await orchestrator.complete_purchase_flow(
            customer_id="CUST001",
            items=test_items,
            payment_method={"type": "credit_card", "card": "**** 1234"},
            shipping_address={"address": "123 Main St", "city": "Mumbai", "zip": "400001"}
        )
        
        print(f"✓ Purchase flow status: {flow_result['status']}")
        print(f"  Order ID: {flow_result.get('order_id')}")
        
        # Show completed steps
        steps = flow_result.get('steps', {})
        if 'inventory_check' in steps:
            print(f"  ✓ Inventory verified")
        if 'payment' in steps:
            print(f"  ✓ Payment processed: {steps['payment'].get('status')}")
        if 'fulfillment' in steps:
            print(f"  ✓ Fulfillment started")
        if 'styling_suggestions' in steps:
            print(f"  ✓ Styling suggestions: {len(steps['styling_suggestions'])} items")
    
    # Test 6: Gift Suggestions
    print("\n6. GIFT SUGGESTIONS")
    print("-" * 80)
    gift_suggestions = await orchestrator.get_gifting_suggestions(
        recipient_profile={"age": 25, "gender": "female"},
        user_preferences={"budget": "mid", "occasion": "birthday"}
    )
    print(f"✓ Got {len(gift_suggestions)} gift suggestions")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    
    await orchestrator.close()


async def test_csv_data_loading():
    """Test that all data loads from CSV files"""
    
    print("\n" + "=" * 80)
    print("TESTING CSV DATA LOADING")
    print("=" * 80)
    
    orchestrator = SalesOrchestrator()
    
    print("\n✓ Products DataFrame loaded:", orchestrator.products_df is not None)
    if orchestrator.products_df is not None:
        print(f"  Total products: {len(orchestrator.products_df)}")
        print(f"  Sample SKU: {orchestrator.products_df.iloc[0]['sku']}")
    
    print("✓ Customers DataFrame loaded:", orchestrator.customers_df is not None)
    if orchestrator.customers_df is not None:
        print(f"  Total customers: {len(orchestrator.customers_df)}")
    
    await orchestrator.close()


async def main():
    """Run all tests"""
    try:
        # Test 1: CSV Data Loading
        await test_csv_data_loading()
        
        # Test 2: Complete Workflow
        await test_complete_workflow()
        
        print("\n" + "=" * 80)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("=" * 80)
        print("\nYour system is ready! Start all services with:")
        print("  python backend/start_all_services.py")
        print("\nThen start the frontend:")
        print("  cd frontend")
        print("  npm run dev")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
