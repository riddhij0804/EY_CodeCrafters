"""
Test script for Post-Purchase Stylist Agent
Tests outfit suggestions, care instructions, and styling recommendations
"""

import requests
import json

BASE_URL = "http://localhost:8006"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_outfit_suggestions():
    """Test outfit suggestions"""
    print_section("TEST 1: Outfit Suggestions - Black Sequined Skirt")
    
    payload = {
        "user_id": "user123",
        "product_sku": "SKU000001",
        "product_name": "Black Sequined Skirt",
        "category": "skirt"
    }
    
    response = requests.post(f"{BASE_URL}/stylist/outfit-suggestions", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_care_instructions():
    """Test care instructions"""
    print_section("TEST 2: Care Instructions - Linen Shirt")
    
    payload = {
        "product_sku": "SKU000015",
        "material": "linen"
    }
    
    response = requests.post(f"{BASE_URL}/stylist/care-instructions", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_occasion_styling():
    """Test occasion-based styling"""
    print_section("TEST 3: AI Occasion Styling - Formal Shirt")
    
    payload = {
        "user_id": "user123",
        "product_sku": "SKU000020",
        "product_name": "White Formal Shirt"
    }
    
    response = requests.post(f"{BASE_URL}/stylist/occasion-styling", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_seasonal_styling():
    """Test seasonal styling"""
    print_section("TEST 4: AI Seasonal Styling - Denim Jacket")
    
    payload = {
        "product_sku": "SKU000025",
        "product_name": "Denim Jacket",
        "product_type": "jacket"
    }
    
    response = requests.post(f"{BASE_URL}/stylist/seasonal-styling", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_fit_feedback():
    """Test fit feedback submission"""
    print_section("TEST 5: Fit Feedback - Size Guidance")
    
    payload = {
        "user_id": "user123",
        "product_sku": "SKU000030",
        "size_purchased": "M",
        "fit_rating": "too_tight",
        "length_feedback": "perfect",
        "comments": "Great quality but runs small"
    }
    
    response = requests.post(f"{BASE_URL}/stylist/fit-feedback", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_multiple_materials():
    """Test care instructions for different materials"""
    print_section("TEST 6: Care Instructions - Multiple Materials")
    
    materials = ["cotton", "silk", "wool", "denim"]
    
    for material in materials:
        print(f"\n🧵 Material: {material.upper()}")
        payload = {
            "product_sku": f"SKU_{material}",
            "material": material
        }
        
        response = requests.post(f"{BASE_URL}/stylist/care-instructions", json=payload)
        result = response.json()
        
        if result.get("success"):
            care = result.get("care_instructions", {})
            print(f"   Washing: {care.get('washing')}")
            print(f"   Drying: {care.get('drying')}")


def test_saree_styling():
    """Test saree-specific styling"""
    print_section("TEST 7: AI Saree Styling - Traditional Silk Saree")
    
    payload = {
        "user_id": "user456",
        "product_sku": "SKU_SAREE001",
        "product_name": "Traditional Silk Saree",
        "category": "saree"
    }
    
    response = requests.post(f"{BASE_URL}/stylist/outfit-suggestions", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    
    if result.get("success"):
        suggestions = result.get("outfit_suggestions", {})
        print("\n👗 Saree Styling Tips:")
        for key, value in suggestions.items():
            print(f"\n{key.upper()}:")
            if isinstance(value, list):
                for item in value:
                    print(f"  • {item}")
            else:
                print(f"  {value}")


def main():
    print("\n" + "👗 "*30)
    print("POST-PURCHASE STYLIST AGENT TESTS")
    print("👗 "*30)
    
    try:
        # Test 1: AI Outfit suggestions
        test_outfit_suggestions()
        
        # Test 2: Care instructions
        test_care_instructions()
        
        # Test 3: AI Occasion styling
        test_occasion_styling()
        
        # Test 4: AI Seasonal styling
        test_seasonal_styling()
        
        # Test 5: Fit feedback
        test_fit_feedback()
        
        # Test 6: Multiple materials
        test_multiple_materials()
        
        # Test 7: AI Saree styling
        test_saree_styling()
        
        print_section("✅ ALL TESTS COMPLETED")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Stylist Agent")
        print("Make sure the agent is running:")
        print("  python backend/agents/worker_agents/stylist/app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

if __name__ == "__main__":
    main()
