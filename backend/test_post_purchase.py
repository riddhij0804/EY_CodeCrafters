"""
Test script for Post-Purchase Support Agent
Tests returns, exchanges, and complaints
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8005"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_get_return_reasons():
    """Test getting list of return reasons"""
    print_section("TEST 1: Get Return Reasons")
    
    response = requests.get(f"{BASE_URL}/post-purchase/return-reasons")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_process_return():
    """Test processing a return request"""
    print_section("TEST 2: Process Return Request")
    
    payload = {
        "user_id": "user123",
        "order_id": "ORDER_001",
        "product_sku": "SKU000001",
        "reason_code": "SIZE_ISSUE",
        "additional_comments": "The shoes are too small, need a larger size"
    }
    
    response = requests.post(f"{BASE_URL}/post-purchase/return", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_process_exchange():
    """Test processing an exchange request"""
    print_section("TEST 3: Process Exchange Request")
    
    payload = {
        "user_id": "user123",
        "order_id": "ORDER_002",
        "product_sku": "SKU000015",
        "current_size": "M",
        "requested_size": "L",
        "reason": "Current size doesn't fit properly"
    }
    
    response = requests.post(f"{BASE_URL}/post-purchase/exchange", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_raise_complaint():
    """Test raising a complaint"""
    print_section("TEST 4: Raise Complaint")
    
    payload = {
        "user_id": "user123",
        "order_id": "ORDER_003",
        "issue_type": "product_quality",
        "description": "The product has a manufacturing defect and is not working properly",
        "priority": "high"
    }
    
    response = requests.post(f"{BASE_URL}/post-purchase/complaint", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_multiple_return_reasons():
    """Test different return reasons"""
    print_section("TEST 5: Multiple Return Reasons")
    
    reasons = [
        "QUALITY_ISSUE",
        "WRONG_ITEM",
        "CHANGED_MIND",
        "DAMAGED_IN_SHIPPING"
    ]
    
    for reason in reasons:
        print(f"\n📦 Testing reason: {reason}")
        payload = {
            "user_id": "user456",
            "order_id": f"ORDER_{reason}",
            "product_sku": "SKU000020",
            "reason_code": reason
        }
        
        response = requests.post(f"{BASE_URL}/post-purchase/return", json=payload)
        result = response.json()
        print(f"   ✅ Return ID: {result.get('return_id')}")
        print(f"   📅 Pickup: {result.get('pickup_date')}")

def test_get_user_returns():
    """Test getting user's return history"""
    print_section("TEST 6: Get User Return History")
    
    response = requests.get(f"{BASE_URL}/post-purchase/returns/user123")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_issue_types():
    """Test getting issue types"""
    print_section("TEST 7: Get Issue Types")
    
    response = requests.get(f"{BASE_URL}/post-purchase/issue-types")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def main():
    print("\n" + "🚀 "*20)
    print("POST-PURCHASE SUPPORT AGENT TESTS")
    print("🚀 "*20)
    
    try:
        # Test 1: Get return reasons
        test_get_return_reasons()
        
        # Test 2: Process return
        test_process_return()
        
        # Test 3: Process exchange
        test_process_exchange()
        
        # Test 4: Raise complaint
        test_raise_complaint()
        
        # Test 5: Multiple return reasons
        test_multiple_return_reasons()
        
        # Test 6: Get user returns
        test_get_user_returns()
        
        # Test 7: Issue types
        test_issue_types()
        
        print_section("✅ ALL TESTS COMPLETED")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Post-Purchase Agent")
        print("Make sure the agent is running:")
        print("  python backend/agents/worker_agents/post_purchase/app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

if __name__ == "__main__":
    main()
