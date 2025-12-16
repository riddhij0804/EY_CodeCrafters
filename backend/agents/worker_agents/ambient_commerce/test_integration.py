# Integration test for Ambient Commerce Agent
# Tests the complete workflow from image upload to product matching

import os
import sys
import requests
import json
from pathlib import Path

# Base URL for the agent
BASE_URL = "http://localhost:8007"

# Test image paths (relative to data directory)
TEST_IMAGES = [
    "../../../data/test_images/test_1.jpg",  
    "../../../data/test_images/test_2.jpg",  
    "../../../data/test_images/test_3.jpg",   
]


def test_health_check():
    """Test the health check endpoint."""
    print("\n" + "="*60)
    print("TEST: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        print("✅ Health check passed")
        print(json.dumps(response.json(), indent=2))
        return True
    else:
        print("❌ Health check failed")
        print(f"Status: {response.status_code}")
        return False


def test_index_info():
    """Test getting index information."""
    print("\n" + "="*60)
    print("TEST: Index Info")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/index/info")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Index info retrieved")
        print(f"Index built: {data['index_built']}")
        print(f"Number of products: {data['num_products']}")
        print(f"Last updated: {data.get('last_updated', 'N/A')}")
        return data['index_built']
    else:
        print("❌ Failed to get index info")
        return False


def test_build_index():
    """Test building the index."""
    print("\n" + "="*60)
    print("TEST: Build Index")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/index/build",
        json={"force_rebuild": False}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Index build successful")
        print(f"Message: {data['message']}")
        print(f"Number of products: {data.get('num_products', 'N/A')}")
        return True
    else:
        print("❌ Index build failed")
        print(f"Status: {response.status_code}")
        print(response.text)
        return False


def test_search_by_path(image_path: str):
    """Test searching for a product by image path."""
    print("\n" + "="*60)
    print(f"TEST: Search by Path - {Path(image_path).name}")
    print("="*60)
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return False
    
    response = requests.post(
        f"{BASE_URL}/search",
        json={
            "image_path": image_path,
            "top_k": 3,
            "similarity_threshold": 0.8
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        
        if data['success']:
            print("✅ Search successful")
            print(f"\nQuery image: {Path(data['query_image']).name}")
            print(f"Number of matches: {data['num_matches']}")
            
            # Best match
            if data['best_match']:
                best = data['best_match']
                print(f"\n🏆 BEST MATCH:")
                print(f"   SKU: {best['matched_product_id']}")
                print(f"   Product: {best['product_name']}")
                print(f"   Brand: {best['brand']}")
                print(f"   Similarity: {best['similarity_score']:.2%}")
                print(f"   Price: ₹{best['price']:.2f}")
                print(f"   Color: {best['color']}")
                print(f"   Sizes: {', '.join(best['size'])}")
                print(f"\n   Reasoning: {best['reasoning']}")
            
            # Alternative matches
            if data['alternative_matches']:
                print(f"\n📋 ALTERNATIVE MATCHES:")
                for i, alt in enumerate(data['alternative_matches'], 1):
                    print(f"\n   {i}. {alt['product_name']}")
                    print(f"      SKU: {alt['matched_product_id']}")
                    print(f"      Similarity: {alt['similarity_score']:.2%}")
                    print(f"      Brand: {alt['brand']}")
            
            # Variants
            if data['available_variants']:
                print(f"\n🎨 AVAILABLE VARIANTS ({len(data['available_variants'])})")
                for variant in data['available_variants'][:5]:  # Show first 5
                    print(f"   - {variant['color']} | ₹{variant['price']:.2f} | {variant['sku']}")
            
            print(f"\n📊 METADATA:")
            print(f"   Threshold: {data['search_metadata']['similarity_threshold']}")
            print(f"   Multiple matches: {data['search_metadata']['returned_multiple']}")
            
            return True
        else:
            print("❌ Search failed")
            print(f"Message: {data['message']}")
            return False
    else:
        print("❌ Search request failed")
        print(f"Status: {response.status_code}")
        print(response.text)
        return False


def test_get_variants():
    """Test getting variants for a specific SKU."""
    print("\n" + "="*60)
    print("TEST: Get Product Variants")
    print("="*60)
    
    test_sku = "SKU000013"
    response = requests.get(f"{BASE_URL}/product/{test_sku}/variants")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Variants retrieved")
        print(f"SKU: {data['sku']}")
        print(f"Number of variants: {data['num_variants']}")
        
        for i, variant in enumerate(data['variants'], 1):
            print(f"\n{i}. {variant['product_name']}")
            print(f"   Color: {variant['color']}")
            print(f"   Price: ₹{variant['price']:.2f}")
            print(f"   Sizes: {', '.join(variant['size'])}")
        
        return True
    else:
        print("❌ Failed to get variants")
        print(f"Status: {response.status_code}")
        return False


def test_upload_search():
    """Test searching by uploading an image file."""
    print("\n" + "="*60)
    print("TEST: Upload and Search")
    print("="*60)
    
    test_image = TEST_IMAGES[0]
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return False
    
    with open(test_image, 'rb') as f:
        files = {'file': (Path(test_image).name, f, 'image/jpeg')}
        data = {
            'top_k': 3,
            'similarity_threshold': 0.8
        }
        
        response = requests.post(
            f"{BASE_URL}/search/upload",
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        result = response.json()
        
        if result['success']:
            print("✅ Upload search successful")
            best = result['best_match']
            print(f"\nMatched: {best['product_name']}")
            print(f"Similarity: {best['similarity_score']:.2%}")
            return True
        else:
            print("❌ Upload search failed")
            return False
    else:
        print("❌ Upload request failed")
        print(f"Status: {response.status_code}")
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "🧪"*30)
    print(" AMBIENT COMMERCE AGENT - INTEGRATION TESTS")
    print("🧪"*30)
    
    results = {}
    
    # Test 1: Health check
    results['health_check'] = test_health_check()
    
    # Test 2: Index info
    index_exists = test_index_info()
    results['index_info'] = index_exists
    
    # Test 3: Build index (if needed)
    if not index_exists:
        results['build_index'] = test_build_index()
    else:
        print("\n✅ Index already exists, skipping build")
        results['build_index'] = True
    
    # Test 4: Search by path (multiple images)
    search_results = []
    for test_image in TEST_IMAGES:
        if os.path.exists(test_image):
            search_results.append(test_search_by_path(test_image))
    results['search_by_path'] = all(search_results) if search_results else False
    
    # Test 5: Get variants
    results['get_variants'] = test_get_variants()
    
    # Test 6: Upload search
    results['upload_search'] = test_upload_search()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ Server is not responding correctly")
            print("Please start the server with: python app.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at", BASE_URL)
        print("Please start the server with: python app.py")
        sys.exit(1)
    
    # Run tests
    success = run_all_tests()
    
    sys.exit(0 if success else 1)
