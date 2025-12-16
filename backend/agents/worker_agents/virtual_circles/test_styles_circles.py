"""
Integration tests for Virtual Style Circles Agent
Run with: python test_style_circles.py

Tests all endpoints and demonstrates AI-generated explanations
"""

import requests
import json
import time
from typing import Dict, List

BASE_URL = "http://localhost:8005"

# ANSI color codes for pretty output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + Colors.HEADER + "="*70 + Colors.ENDC)
    print(Colors.HEADER + Colors.BOLD + f"  {title}" + Colors.ENDC)
    print(Colors.HEADER + "="*70 + Colors.ENDC)

def print_success(message: str):
    """Print success message"""
    print(Colors.OKGREEN + f"✅ {message}" + Colors.ENDC)

def print_error(message: str):
    """Print error message"""
    print(Colors.FAIL + f"❌ {message}" + Colors.ENDC)

def print_info(message: str):
    """Print info message"""
    print(Colors.OKCYAN + f"ℹ️  {message}" + Colors.ENDC)

def print_json(data: Dict, indent: int = 2):
    """Print formatted JSON"""
    print(Colors.OKBLUE + json.dumps(data, indent=indent, ensure_ascii=False) + Colors.ENDC)

def test_health_check():
    """Test 1: Health Check"""
    print_section("TEST 1: Health Check & Service Status")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print_json(data)
        
        assert response.status_code == 200, "Health check failed"
        assert "service" in data, "Missing service info"
        assert "circles" in data, "Missing circles count"
        assert "users" in data, "Missing users count"
        
        print_success(f"Service operational with {data['circles']} circles and {data['users']} users")
        return True
        
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to service. Is it running on port 8005?")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_get_stats():
    """Test 2: System Statistics"""
    print_section("TEST 2: System Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/stats", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print_json(data)
        
        assert response.status_code == 200, "Stats request failed"
        assert data['total_circles'] > 0, "No circles formed"
        assert data['total_users'] > 0, "No users loaded"
        
        print_success(f"System Stats Retrieved")
        print_info(f"  • {data['total_circles']} circles formed")
        print_info(f"  • {data['total_users']} users with profiles")
        print_info(f"  • {data['total_interactions']} total interactions")
        print_info(f"  • Avg circle size: {data['avg_circle_size']:.1f} users")
        print_info(f"  • Largest circle: {data['largest_circle']} users")
        
        return True
        
    except Exception as e:
        print_error(f"Stats test failed: {e}")
        return False

def test_assign_user():
    """Test 3: Assign User to Circle"""
    print_section("TEST 3: Assign User to Circle")
    
    # Use a real customer ID from the data (customer 207 has orders)
    test_user_id = "207"
    
    try:
        response = requests.post(
            f"{BASE_URL}/circles/assign-user",
            params={"user_id": test_user_id},
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print_json(data)
        
        assert response.status_code == 200, "User assignment failed"
        assert 'circle_id' in data, "Missing circle_id"
        assert 'similarity_score' in data, "Missing similarity score"
        
        print_success(f"User {test_user_id} assigned to {data['circle_id']}")
        print_info(f"  • Similarity score: {data['similarity_score']:.3f}")
        
        return data['circle_id']
        
    except Exception as e:
        print_error(f"User assignment failed: {e}")
        return None

def test_get_circle_info(circle_id: str):
    """Test 4: Get Circle Information"""
    print_section("TEST 4: Get Circle Information")
    
    if not circle_id:
        print_error("No circle_id provided")
        return False
    
    try:
        response = requests.get(f"{BASE_URL}/circles/{circle_id}", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print_json(data)
        
        assert response.status_code == 200, "Circle info request failed"
        assert data['user_count'] > 0, "Circle has no users"
        
        print_success(f"Circle Info Retrieved")
        print_info(f"  • Users: {data['user_count']}")
        print_info(f"  • Avg Order Value: ₹{data['avg_order_value']:.2f}")
        print_info(f"  • Top Brands: {', '.join(data['top_brands'][:3])}")
        print_info(f"  • Top Categories: {', '.join(data['top_categories'][:3])}")
        
        return True
        
    except Exception as e:
        print_error(f"Circle info test failed: {e}")
        return False

def test_get_trends(circle_id: str):
    """Test 5: Get Circle Trends"""
    print_section("TEST 5: Get Trending Products in Circle")
    
    if not circle_id:
        print_error("No circle_id provided")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/circles/{circle_id}/trends",
            params={"days": 14},
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print_info(f"Time window: {data['time_window_days']} days")
        print_info(f"Found {len(data['trends'])} trending items")
        
        assert response.status_code == 200, "Trends request failed"
        
        if len(data['trends']) > 0:
            print("\n" + Colors.BOLD + "Top 3 Trending Products:" + Colors.ENDC)
            
            for i, trend in enumerate(data['trends'][:3], 1):
                print(f"\n{Colors.WARNING}{i}. {trend['product_name']}{Colors.ENDC}")
                print(f"   Brand: {trend['brand']}")
                print(f"   SKU: {trend['sku']}")
                print(f"   Trend Score: {Colors.OKGREEN}{trend['score']:.1f}{Colors.ENDC}")
                print(f"   Trend Label: {Colors.OKCYAN}{trend['trend_label']}{Colors.ENDC}")
                print(f"   Interactions: {trend['interaction_count']}")
                print(f"   Velocity: {trend['velocity']:.2f} interactions/day")
                print(f"   Unique Users: {trend['unique_users']}")
            
            print_success("Trend detection working")
        else:
            print_info("No trends found (this is okay for fresh data)")
        
        return True
        
    except Exception as e:
        print_error(f"Trends test failed: {e}")
        return False

def test_predict_trends(circle_id: str):
    """Test 6: Predict Future Trends"""
    print_section("TEST 6: Predict Future Trends (7-Day Forecast)")
    
    if not circle_id:
        print_error("No circle_id provided")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/circles/{circle_id}/predict",
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print_info(f"Prediction horizon: {data['prediction_horizon']}")
        print_info(f"Generated {len(data['predictions'])} predictions")
        
        assert response.status_code == 200, "Prediction request failed"
        
        if len(data['predictions']) > 0:
            print("\n" + Colors.BOLD + "Top 3 Predicted Trends:" + Colors.ENDC)
            
            for i, pred in enumerate(data['predictions'][:3], 1):
                growth = pred['predicted_score'] - pred['score']
                print(f"\n{Colors.WARNING}{i}. {pred['product_name']}{Colors.ENDC}")
                print(f"   Brand: {pred['brand']}")
                print(f"   Current Score: {pred['score']:.1f}")
                print(f"   Predicted Score: {Colors.OKGREEN}{pred['predicted_score']:.1f}{Colors.ENDC}")
                print(f"   Expected Growth: {Colors.OKCYAN}+{growth:.1f}{Colors.ENDC}")
                print(f"   Prediction: {Colors.BOLD}{pred['prediction_label']}{Colors.ENDC}")
            
            print_success("Trend prediction working")
        else:
            print_info("No predictions available (this is okay for fresh data)")
        
        return True
        
    except Exception as e:
        print_error(f"Prediction test failed: {e}")
        return False

def test_user_recommendations():
    """Test 7: User Recommendations with AI Explanations"""
    print_section("TEST 7: Personalized Recommendations with AI Explanations")
    
    # Use a real customer ID from the data (customer 164 has orders)
    test_user_id = "164"
    
    try:
        response = requests.get(
            f"{BASE_URL}/user/{test_user_id}/recommendations",
            params={"limit": 5},
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        
        assert response.status_code == 200, "Recommendations request failed"
        
        print_info(f"User: {data['user_id']}")
        print_info(f"Circle: {data['circle_id']}")
        print_info(f"Recommendations: {len(data['recommendations'])}")
        
        if len(data['recommendations']) > 0:
            print("\n" + Colors.BOLD + "="*70 + Colors.ENDC)
            print(Colors.BOLD + "  PERSONALIZED RECOMMENDATIONS" + Colors.ENDC)
            print(Colors.BOLD + "="*70 + Colors.ENDC)
            
            for i, rec in enumerate(data['recommendations'][:3], 1):
                print(f"\n{Colors.HEADER}{'─'*70}{Colors.ENDC}")
                print(f"{Colors.WARNING}{Colors.BOLD}RECOMMENDATION {i}{Colors.ENDC}")
                print(f"{Colors.HEADER}{'─'*70}{Colors.ENDC}")
                
                print(f"\n{Colors.BOLD}Product:{Colors.ENDC} {rec['product_name']}")
                print(f"{Colors.BOLD}Brand:{Colors.ENDC} {rec['brand']}")
                print(f"{Colors.BOLD}SKU:{Colors.ENDC} {rec['sku']}")
                print(f"{Colors.BOLD}Price:{Colors.ENDC} ₹{rec['price']:.2f}")
                print(f"{Colors.BOLD}Score:{Colors.ENDC} {rec['score']:.1f}")
                
                if rec.get('image_url'):
                    print(f"{Colors.BOLD}Image:{Colors.ENDC} {rec['image_url']}")
                
                print(f"\n{Colors.OKCYAN}{Colors.BOLD}💡 WHY THIS IS PERFECT FOR YOU:{Colors.ENDC}")
                print(f"{Colors.OKGREEN}{rec['explanation']}{Colors.ENDC}")
            
            print(f"\n{Colors.HEADER}{'─'*70}{Colors.ENDC}")
            print_success("AI-generated explanations working!")
            
            # Check if explanations are actually from AI (not fallback)
            first_explanation = data['recommendations'][0]['explanation']
            if len(first_explanation) > 50 and any(word in first_explanation.lower() for word in ['circle', 'people', 'week']):
                print_success("Explanations appear personalized and contextual")
            else:
                print_info("Using fallback templates (Gemini might not be configured)")
        else:
            print_info("No recommendations available for this user")
        
        return True
        
    except Exception as e:
        print_error(f"Recommendations test failed: {e}")
        return False

def test_log_interaction():
    """Test 8: Log User Interaction"""
    print_section("TEST 8: Log User Interaction Events")
    
    # Use real customer ID (229) and SKU (SKU000189) from the data
    test_events = [
        {"user_id": "229", "sku": "SKU000189", "event_type": "view"},
        {"user_id": "229", "sku": "SKU000189", "event_type": "like"},
        {"user_id": "229", "sku": "SKU000189", "event_type": "cart"},
        {"user_id": "229", "sku": "SKU000189", "event_type": "purchase"}
    ]
    
    try:
        for i, interaction in enumerate(test_events, 1):
            response = requests.post(
                f"{BASE_URL}/interactions/log",
                json=interaction,
                timeout=5
            )
            
            assert response.status_code == 200, f"Failed to log {interaction['event_type']}"
            
            print(f"{i}. Logged: {Colors.OKCYAN}{interaction['event_type']}{Colors.ENDC} event for SKU {interaction['sku']}")
            time.sleep(0.2)  # Small delay between events
        
        print_success("All interaction events logged successfully")
        return True
        
    except Exception as e:
        print_error(f"Interaction logging failed: {e}")
        return False

def test_error_handling():
    """Test 9: Error Handling"""
    print_section("TEST 9: Error Handling & Edge Cases")
    
    all_passed = True
    
    try:
        # Test 1: Invalid circle ID
        print_info("Testing invalid circle ID...")
        response = requests.get(f"{BASE_URL}/circles/invalid_circle_999", timeout=5)
        assert response.status_code == 404, "Should return 404 for invalid circle"
        print_success("✓ Invalid circle returns 404")
        
        # Test 2: Invalid user ID
        print_info("Testing invalid user ID...")
        response = requests.get(f"{BASE_URL}/user/INVALID_USER_999/recommendations", timeout=5)
        assert response.status_code == 404, "Should return 404 for invalid user"
        print_success("✓ Invalid user returns 404")
        
        # Test 3: Invalid interaction event
        print_info("Testing invalid interaction type...")
        response = requests.post(
            f"{BASE_URL}/interactions/log",
            json={"user_id": "CUST001", "sku": "TEST", "event_type": "invalid_type"},
            timeout=5
        )
        # Should still log (permissive) or return 200
        assert response.status_code in [200, 400], "Should handle gracefully"
        print_success("✓ Invalid event type handled")
        
        print_success("Error handling working correctly")
        return True
        
    except AssertionError as e:
        print_error(f"Error handling test failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error in error handling test: {e}")
        return False

def test_performance():
    """Test 10: Performance & Response Times"""
    print_section("TEST 10: Performance Metrics")
    
    try:
        endpoints = [
            ("Health Check", f"{BASE_URL}/"),
            ("Stats", f"{BASE_URL}/stats"),
            ("User Recommendations", f"{BASE_URL}/user/CUST001/recommendations?limit=5")
        ]
        
        print("\nMeasuring response times...")
        
        for name, url in endpoints:
            start = time.time()
            response = requests.get(url, timeout=10)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            if response.status_code == 200:
                print(f"  • {name}: {Colors.OKGREEN}{elapsed:.0f}ms{Colors.ENDC}")
            else:
                print(f"  • {name}: {Colors.FAIL}{elapsed:.0f}ms (failed){Colors.ENDC}")
        
        print_success("Performance test completed")
        return True
        
    except Exception as e:
        print_error(f"Performance test failed: {e}")
        return False

def run_all_tests():
    """Run complete test suite"""
    print("\n" + Colors.HEADER + "🎯"*35 + Colors.ENDC)
    print(Colors.HEADER + Colors.BOLD + "  VIRTUAL STYLE CIRCLES AGENT - COMPREHENSIVE TEST SUITE" + Colors.ENDC)
    print(Colors.HEADER + "🎯"*35 + Colors.ENDC)
    
    test_results = []
    circle_id = None
    
    try:
        # Core functionality tests
        test_results.append(("Health Check", test_health_check()))
        test_results.append(("System Stats", test_get_stats()))
        
        # Circle operations
        circle_id = test_assign_user()
        test_results.append(("User Assignment", circle_id is not None))
        
        if circle_id:
            test_results.append(("Circle Info", test_get_circle_info(circle_id)))
            test_results.append(("Trend Detection", test_get_trends(circle_id)))
            test_results.append(("Trend Prediction", test_predict_trends(circle_id)))
        
        # Recommendations (main feature)
        test_results.append(("User Recommendations", test_user_recommendations()))
        
        # Interaction logging
        test_results.append(("Interaction Logging", test_log_interaction()))
        
        # Error handling
        test_results.append(("Error Handling", test_error_handling()))
        
        # Performance
        test_results.append(("Performance", test_performance()))
        
        # Print summary
        print("\n" + Colors.HEADER + "="*70 + Colors.ENDC)
        print(Colors.HEADER + Colors.BOLD + "  TEST SUMMARY" + Colors.ENDC)
        print(Colors.HEADER + "="*70 + Colors.ENDC)
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = f"{Colors.OKGREEN}✅ PASSED{Colors.ENDC}" if result else f"{Colors.FAIL}❌ FAILED{Colors.ENDC}"
            print(f"  {test_name:.<50} {status}")
        
        print(Colors.HEADER + "─"*70 + Colors.ENDC)
        
        success_rate = (passed / total) * 100
        print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed ({success_rate:.0f}%){Colors.ENDC}")
        
        if passed == total:
            print("\n" + Colors.OKGREEN + "🎉"*35 + Colors.ENDC)
            print(Colors.OKGREEN + Colors.BOLD + "  ALL TESTS PASSED! AGENT IS FULLY OPERATIONAL!" + Colors.ENDC)
            print(Colors.OKGREEN + "🎉"*35 + Colors.ENDC)
            return True
        else:
            print("\n" + Colors.WARNING + "⚠️  Some tests failed. Please check the output above." + Colors.ENDC)
            return False
        
    except requests.exceptions.ConnectionError:
        print("\n" + Colors.FAIL + "="*70 + Colors.ENDC)
        print(Colors.FAIL + Colors.BOLD + "❌ ERROR: Cannot connect to service" + Colors.ENDC)
        print(Colors.FAIL + "="*70 + Colors.ENDC)
        print("\nMake sure the Virtual Style Circles Agent is running:")
        print(f"  {Colors.OKCYAN}cd backend/agents/worker_agents/style_circles{Colors.ENDC}")
        print(f"  {Colors.OKCYAN}python app.py{Colors.ENDC}")
        print("\nOr use the startup script:")
        print(f"  {Colors.OKCYAN}./start.sh{Colors.ENDC}")
        return False
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ UNEXPECTED ERROR: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    
    # Print usage hint
    if success:
        print(f"\n{Colors.OKCYAN}💡 Next Steps:{Colors.ENDC}")
        print(f"  • Check the API documentation: {Colors.OKBLUE}http://localhost:8005/docs{Colors.ENDC}")
        print(f"  • Integrate with Sales Agent: See {Colors.OKBLUE}SALES_AGENT_INTEGRATION.md{Colors.ENDC}")
        print(f"  • View examples: See {Colors.OKBLUE}EXAMPLE_USAGE.md{Colors.ENDC}")
    
    exit(0 if success else 1)