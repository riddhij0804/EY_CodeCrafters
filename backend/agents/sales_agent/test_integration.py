# Quick Integration Test
# Run this to verify Sales Agent can connect to Inventory Agent

import sys
sys.path.append('.')

from inventory_client import get_inventory_client

def test_integration():
    """Test Sales Agent → Inventory Agent connectivity."""
    
    print("=" * 70)
    print("🔗 SALES AGENT ↔ INVENTORY AGENT INTEGRATION TEST")
    print("=" * 70)
    
    # Initialize client
    print("\n1️⃣ Initializing inventory client...")
    client = get_inventory_client()
    print("   ✅ Client created")
    
    # Health check
    print("\n2️⃣ Checking inventory service health...")
    try:
        healthy = client.health_check()
        if healthy:
            print("   ✅ Inventory service is healthy")
        else:
            print("   ❌ Inventory service is unhealthy")
            print("\n💡 Start the inventory service:")
            print("   cd backend/agents/worker_agents/inventory")
            print("   python app.py")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to inventory service: {e}")
        print("\n💡 Make sure inventory service is running on http://localhost:8001")
        return False
    
    # Test get inventory
    print("\n3️⃣ Testing GET /inventory/{sku}...")
    try:
        stock = client.get_inventory("SKU000001")
        print(f"   ✅ Retrieved stock for SKU000001:")
        print(f"      • Online: {stock['online_stock']} units")
        print(f"      • Total: {stock['total_stock']} units")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test create hold
    print("\n4️⃣ Testing POST /hold (create inventory hold)...")
    try:
        hold = client.create_hold(
            sku="SKU000001",
            quantity=1,
            location="online",
            ttl=60,
            idempotency_key="integration-test-001"
        )
        print(f"   ✅ Hold created:")
        print(f"      • Hold ID: {hold['hold_id']}")
        print(f"      • Remaining stock: {hold['remaining_stock']}")
        hold_id = hold['hold_id']
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test release hold
    print("\n5️⃣ Testing POST /release (release hold)...")
    try:
        result = client.release_hold(hold_id)
        print(f"   ✅ Hold released:")
        print(f"      • Status: {result['status']}")
        print(f"      • Restored stock: {result['restored_stock']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test check availability
    print("\n6️⃣ Testing availability check (convenience method)...")
    try:
        available = client.check_availability("SKU000001", quantity=10, location="online")
        print(f"   ✅ Availability check:")
        print(f"      • 10 units available: {'Yes' if available else 'No'}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Success
    print("\n" + "=" * 70)
    print("✅ ALL INTEGRATION TESTS PASSED!")
    print("=" * 70)
    print("\n💡 You can now use the inventory client in your sales agent:")
    print("   • Import: from inventory_client import get_inventory_client")
    print("   • Usage: client = get_inventory_client()")
    print("   • Check: stock = client.get_inventory('SKU000001')")
    print()
    return True


if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
