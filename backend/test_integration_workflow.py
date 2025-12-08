"""
Integration Test Script for Complete E-Commerce Workflow
=========================================================

This script validates the complete end-to-end customer journey using real CSV data
from the data/ folder. It tests the integration of ALL microservices:
- Inventory Agent (port 8001)
- Payment Agent (port 8003)  
- Fulfillment Agent (port 8004)
- Post-Purchase Agent (port 8005)
- Stylist Agent (port 8006)

The script does NOT modify any agent code or datasets.
It only reads CSV files and makes HTTP calls to the agents.

Author: python test_integration_workflow.pyEY CodeCrafters Team
Date: December 2025
"""

import pandas as pd
import requests
import json
import random
from typing import Dict, Any, List
from pathlib import Path
import sys


# ============================================================================
# CONFIGURATION
# ============================================================================

# Agent URLs
INVENTORY_AGENT_URL = "http://localhost:8001"  # Fixed: Inventory runs on 8001, not 8002
PAYMENT_AGENT_URL = "http://localhost:8003"
FULFILLMENT_AGENT_URL = "http://localhost:8004"
POST_PURCHASE_AGENT_URL = "http://localhost:8005"
STYLIST_AGENT_URL = "http://localhost:8006"

# Data file paths
DATA_DIR = Path(__file__).parent / "data"
ORDERS_FILE = DATA_DIR / "orders.csv"
PAYMENTS_FILE = DATA_DIR / "payments.csv"
INVENTORY_FILE = DATA_DIR / "inventory.csv"
PRODUCTS_FILE = DATA_DIR / "products.csv"
STORES_FILE = DATA_DIR / "stores.csv"

# Request timeout
TIMEOUT = 10


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_datasets() -> Dict[str, pd.DataFrame]:
    """Load all CSV datasets into pandas DataFrames."""
    print("=" * 80)
    print("LOADING DATASETS")
    print("=" * 80)
    
    datasets = {}
    
    try:
        datasets['orders'] = pd.read_csv(ORDERS_FILE)
        print(f"✓ Loaded {len(datasets['orders'])} orders from {ORDERS_FILE}")
        
        datasets['payments'] = pd.read_csv(PAYMENTS_FILE)
        print(f"✓ Loaded {len(datasets['payments'])} payments from {PAYMENTS_FILE}")
        
        datasets['inventory'] = pd.read_csv(INVENTORY_FILE)
        print(f"✓ Loaded {len(datasets['inventory'])} inventory records from {INVENTORY_FILE}")
        
        datasets['products'] = pd.read_csv(PRODUCTS_FILE)
        print(f"✓ Loaded {len(datasets['products'])} products from {PRODUCTS_FILE}")
        
        datasets['stores'] = pd.read_csv(STORES_FILE)
        print(f"✓ Loaded {len(datasets['stores'])} stores from {STORES_FILE}")
        
        print("\nDatasets loaded successfully!\n")
        return datasets
        
    except FileNotFoundError as e:
        print(f"✗ Error: Could not find file - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading datasets: {e}")
        sys.exit(1)


# ============================================================================
# AGENT INTEGRATION FUNCTIONS
# ============================================================================

def check_inventory_availability(sku: str, quantity: int, inventory_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Call Inventory Agent to check stock availability and create a hold.
    
    Since inventory is distributed across stores (STORE_MUMBAI, STORE_DELHI, etc.),
    this function finds a store with sufficient stock and creates a hold there.
    
    Args:
        sku: Product SKU
        quantity: Quantity to reserve
        inventory_df: DataFrame containing inventory records (sku, store_id, qty)
        
    Returns:
        dict with keys: success, hold_id, message, available_qty, location
    """
    try:
        # Find stores with this SKU
        sku_inventory = inventory_df[inventory_df['sku'] == sku]
        
        if sku_inventory.empty:
            return {
                "success": False,
                "hold_id": None,
                "message": f"SKU {sku} not found in any store",
                "available_qty": 0,
                "location": None
            }
        
        # Calculate total available across all stores
        total_available = sku_inventory['qty'].sum()
        
        # Find a store with sufficient stock
        sufficient_stores = sku_inventory[sku_inventory['qty'] >= quantity]
        
        if sufficient_stores.empty:
            return {
                "success": False,
                "hold_id": None,
                "message": f"Insufficient stock: need {quantity}, total available {total_available} (spread across {len(sku_inventory)} stores)",
                "available_qty": total_available,
                "location": None
            }
        
        # Pick the store with most stock
        best_store = sufficient_stores.loc[sufficient_stores['qty'].idxmax()]
        store_id = best_store['store_id']
        store_qty = best_store['qty']
        
        # Now attempt to create a hold at this specific store
        # IMPORTANT: Inventory Agent expects "store:STORE_ID" format, not just "STORE_ID"
        location = f"store:{store_id}" if not store_id.startswith("store:") else store_id
        
        hold_request = {
            "sku": sku,
            "quantity": quantity,
            "location": location,  # Format: "store:STORE_MUMBAI"
            "ttl": 600  # 10 minute hold
        }
        
        hold_response = requests.post(
            f"{INVENTORY_AGENT_URL}/hold",
            json=hold_request,
            timeout=TIMEOUT
        )
        
        if hold_response.status_code == 200:
            hold_data = hold_response.json()
            return {
                "success": True,
                "hold_id": hold_data.get("hold_id"),
                "message": f"Successfully reserved {quantity} units of {sku} from {store_id}",
                "available_qty": total_available,
                "location": store_id
            }
        else:
            error_detail = hold_response.json().get("detail", "Unknown error")
            return {
                "success": False,
                "hold_id": None,
                "message": f"Hold failed at {store_id}: {error_detail} (Store has {store_qty} units)",
                "available_qty": total_available,
                "location": store_id
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "hold_id": None,
            "message": "Cannot connect to Inventory Agent. Is it running on port 8001?",
            "available_qty": 0,
            "location": None
        }
    except Exception as e:
        return {
            "success": False,
            "hold_id": None,
            "message": f"Inventory error: {str(e)}",
            "available_qty": 0,
            "location": None
        }


def process_payment(order_id: str, customer_id: str, amount: float, payments_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Process payment via Payment Agent API.
    
    First checks if payment exists in CSV for this order. If it exists and is successful,
    returns that payment ID. Otherwise, calls the Payment Agent to process a new payment.
    
    Args:
        order_id: Order ID
        customer_id: Customer ID
        amount: Payment amount
        payments_df: DataFrame containing historical payment records
        
    Returns:
        dict with keys: success, payment_id, transaction_id, status, amount, method
    """
    try:
        # First check if payment already exists in CSV
        payment_record = payments_df[payments_df['order_id'] == order_id]
        
        if not payment_record.empty:
            payment = payment_record.iloc[0]
            payment_status = payment['status'].lower()
            
            # If payment already succeeded, use existing payment ID
            if payment_status == "success":
                return {
                    "success": True,
                    "payment_id": payment['payment_id'],
                    "transaction_id": payment['payment_id'],  # Use same ID
                    "status": payment_status,
                    "amount": payment['amount_rupees'],
                    "method": payment['method'],
                    "message": f"Payment already processed: ₹{payment['amount_rupees']} via {payment['method']} (CSV record)"
                }
            else:
                # Payment exists but failed/pending - try to process new payment
                print(f"   ⚠ Existing payment {payment_status}, attempting new payment via Payment Agent...")
        
        # Call Payment Agent to process payment
        payment_request = {
            "user_id": str(customer_id),
            "amount": float(amount),
            "payment_method": "upi",  # Default method for testing
            "order_id": order_id,
            "metadata": {
                "source": "integration_test",
                "test_mode": True
            }
        }
        
        response = requests.post(
            f"{PAYMENT_AGENT_URL}/payment/process",
            json=payment_request,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            payment_data = response.json()
            return {
                "success": payment_data.get("success", False),
                "payment_id": payment_data.get("transaction_id"),
                "transaction_id": payment_data.get("transaction_id"),
                "status": "success" if payment_data.get("success") else "failed",
                "amount": payment_data.get("amount", amount),
                "method": payment_data.get("payment_method", "upi"),
                "message": f"Payment processed via Payment Agent: ₹{payment_data.get('amount')} - {payment_data.get('message')}"
            }
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return {
                "success": False,
                "payment_id": None,
                "transaction_id": None,
                "status": "failed",
                "amount": amount,
                "method": None,
                "message": f"Payment API failed: {error_detail}"
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "payment_id": None,
            "transaction_id": None,
            "status": "failed",
            "amount": 0.0,
            "method": None,
            "message": "Cannot connect to Payment Agent. Is it running on port 8003?"
        }
    except Exception as e:
        return {
            "success": False,
            "payment_id": None,
            "transaction_id": None,
            "status": "failed",
            "amount": 0.0,
            "method": None,
            "message": f"Payment error: {str(e)}"
        }


def start_fulfillment(order_id: str, hold_id: str, payment_id: str, 
                      total_amount: float) -> Dict[str, Any]:
    """
    Call Fulfillment Agent to start order fulfillment.
    
    Args:
        order_id: Order ID
        hold_id: Inventory hold ID
        payment_id: Payment transaction ID
        total_amount: Order total amount
        
    Returns:
        dict with keys: success, fulfillment_id, tracking_id, status, courier, eta
    """
    try:
        fulfillment_request = {
            "order_id": order_id,
            "inventory_status": "RESERVED",  # Required by fulfillment agent
            "payment_status": "SUCCESS",      # Required by fulfillment agent
            "amount": total_amount,  # Fixed: Fulfillment agent expects 'amount', not 'total_amount'
            "inventory_hold_id": hold_id,
            "payment_transaction_id": payment_id
        }
        
        response = requests.post(
            f"{FULFILLMENT_AGENT_URL}/fulfillment/start",
            json=fulfillment_request,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            fulfillment = data.get("fulfillment", {})
            return {
                "success": True,
                "fulfillment_id": fulfillment.get("fulfillment_id"),
                "tracking_id": fulfillment.get("tracking_id"),
                "status": fulfillment.get("current_status"),
                "courier": fulfillment.get("courier_partner"),
                "eta": fulfillment.get("eta"),
                "message": data.get("message", "Fulfillment started successfully")
            }
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return {
                "success": False,
                "fulfillment_id": None,
                "tracking_id": None,
                "status": None,
                "courier": None,
                "eta": None,
                "message": f"Fulfillment failed: {error_detail}"
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "fulfillment_id": None,
            "tracking_id": None,
            "status": None,
            "courier": None,
            "eta": None,
            "message": "Cannot connect to Fulfillment Agent. Is it running on port 8004?"
        }
    except Exception as e:
        return {
            "success": False,
            "fulfillment_id": None,
            "tracking_id": None,
            "status": None,
            "courier": None,
            "eta": None,
            "message": f"Fulfillment error: {str(e)}"
        }


def test_post_purchase_return(order_id: str, customer_id: int, order_items: List[Dict], datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Call Post-Purchase Agent to test return functionality.
    
    Args:
        order_id: Order ID
        customer_id: Customer ID
        order_items: List of items in the order
        datasets: Dict of pandas DataFrames
        
    Returns:
        dict with keys: success, return_id, status, message
    """
    try:
        # Test return for first item in order
        first_item = order_items[0]
        
        return_request = {
            "user_id": str(customer_id),
            "order_id": order_id,
            "product_sku": first_item['sku'],
            "reason_code": "QUALITY_ISSUE",
            "additional_comments": "Quality issue - Integration test"
        }
        
        response = requests.post(
            f"{POST_PURCHASE_AGENT_URL}/post-purchase/return",
            json=return_request,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "return_id": data.get("return_id"),
                "status": data.get("status"),
                "refund_amount": data.get("refund_amount"),
                "message": f"Return initiated successfully for {first_item['sku']}"
            }
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return {
                "success": False,
                "return_id": None,
                "status": None,
                "refund_amount": 0.0,
                "message": f"Return failed: {error_detail}"
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "return_id": None,
            "status": None,
            "refund_amount": 0.0,
            "message": "Cannot connect to Post-Purchase Agent. Is it running on port 8005?"
        }
    except Exception as e:
        return {
            "success": False,
            "return_id": None,
            "status": None,
            "refund_amount": 0.0,
            "message": f"Post-purchase error: {str(e)}"
        }


def test_stylist_recommendations(customer_id: int, order_items: List[Dict], datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Call Stylist Agent to get AI outfit recommendations.
    
    Args:
        customer_id: Customer ID
        order_items: List of items purchased
        datasets: Dict of pandas DataFrames
        
    Returns:
        dict with keys: success, recommendations, message
    """
    try:
        # Get outfit suggestions based on purchased items
        first_item = order_items[0]
        sku = first_item['sku']
        
        # Get product details from products.csv
        products_df = datasets['products']
        product = products_df[products_df['sku'] == sku]
        
        if product.empty:
            return {
                "success": False,
                "recommendations": 0,
                "ai_used": False,
                "message": f"Product {sku} not found in catalog"
            }
        
        product_details = product.iloc[0]
        
        # Convert pandas null/NaN to None, and handle missing fields
        color = product_details.get('BaseColour')
        if pd.isna(color):
            color = None
        
        brand = product_details.get('brand')
        if pd.isna(brand):
            brand = None
        
        stylist_request = {
            "user_id": str(customer_id),
            "product_sku": sku,
            "product_name": str(product_details['ProductDisplayName']),
            "category": str(product_details['category']),
            "color": color,
            "brand": brand
        }
        
        response = requests.post(
            f"{STYLIST_AGENT_URL}/stylist/outfit-suggestions",
            json=stylist_request,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            # API returns recommendations object with recommended_products array
            recommendations_obj = data.get("recommendations", {})
            recommended_products = recommendations_obj.get("recommended_products", [])
            styling_tips = recommendations_obj.get("styling_tips", [])
            purchased_product = data.get("purchased_product", {})
            
            # Format purchased product info
            purchased_info = f"{purchased_product.get('name', 'Unknown')} ({purchased_product.get('category', 'N/A')})"
            
            return {
                "success": True,
                "recommendations": len(recommended_products),
                "styling_tips": len(styling_tips),
                "ai_used": True,  # API uses Groq AI
                "purchased_product": purchased_info,
                "detailed_recommendations": recommended_products,  # Full list
                "styling_tips_list": styling_tips,  # Full list
                "message": f"AI generated {len(recommended_products)} outfit recommendations with {len(styling_tips)} styling tips"
            }
        else:
            error_detail = response.json().get("detail", "Unknown error")
            return {
                "success": False,
                "recommendations": 0,
                "ai_used": False,
                "message": f"Stylist failed: {error_detail}"
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "recommendations": 0,
            "ai_used": False,
            "message": "Cannot connect to Stylist Agent. Is it running on port 8006?"
        }
    except Exception as e:
        return {
            "success": False,
            "recommendations": 0,
            "ai_used": False,
            "message": f"Stylist error: {str(e)}"
        }


# ============================================================================
# MAIN TEST WORKFLOW
# ============================================================================

def test_full_order_flow(order_id: str, datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Test complete order fulfillment flow for a single order.
    
    Workflow:
    1. Load order details from orders.csv
    2. Extract SKU, quantity, amount
    3. Call Inventory Agent → reserve stock
    4. Verify payment status from payments.csv
    5. If both succeed → Call Fulfillment Agent
    6. Return comprehensive summary
    
    Args:
        order_id: Order ID to test
        datasets: Dict of pandas DataFrames (orders, payments, inventory, etc.)
        
    Returns:
        dict: Complete summary of the workflow execution
    """
    print("\n" + "=" * 80)
    print(f"TESTING ORDER: {order_id}")
    print("=" * 80)
    
    result = {
        "order_id": order_id,
        "inventory_reserved": False,
        "payment_verified": False,
        "fulfillment_started": False,
        "fulfillment_id": None,
        "tracking_id": None,
        "hold_id": None,
        "payment_id": None,
        "errors": []
    }
    
    # Step 1: Load order from CSV
    orders_df = datasets['orders']
    order_record = orders_df[orders_df['order_id'] == order_id]
    
    if order_record.empty:
        error_msg = f"Order {order_id} not found in orders.csv"
        print(f"\n✗ {error_msg}")
        result['errors'].append(error_msg)
        return result
    
    order = order_record.iloc[0]
    print(f"\n📦 Order Details:")
    print(f"   Customer ID: {order['customer_id']}")
    print(f"   Total Amount: ₹{order['total_amount']}")
    print(f"   Status: {order['status']}")
    
    # Parse items (JSON string in CSV)
    try:
        items = json.loads(order['items'])
        print(f"   Items: {len(items)} item(s)")
        
        # For simplicity, test with the first item only
        if not items:
            error_msg = "Order has no items"
            print(f"\n✗ {error_msg}")
            result['errors'].append(error_msg)
            return result
            
        first_item = items[0]
        sku = first_item['sku']
        quantity = first_item['qty']
        
        print(f"\n   Testing with first item:")
        print(f"   → SKU: {sku}")
        print(f"   → Quantity: {quantity}")
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse order items: {e}"
        print(f"\n✗ {error_msg}")
        result['errors'].append(error_msg)
        return result
    
    # Step 2: Reserve Inventory
    print(f"\n🏭 STEP 1: INVENTORY RESERVATION")
    print("-" * 80)
    
    inventory_result = check_inventory_availability(sku, quantity, datasets['inventory'])
    print(f"   Result: {inventory_result['message']}")
    
    if inventory_result['success']:
        print(f"   ✓ Hold ID: {inventory_result['hold_id']}")
        print(f"   ✓ Location: {inventory_result['location']}")
        print(f"   ✓ Total Available: {inventory_result['available_qty']} units (across all stores)")
        result['inventory_reserved'] = True
        result['hold_id'] = inventory_result['hold_id']
    else:
        print(f"   ✗ Inventory reservation failed")
        result['errors'].append(inventory_result['message'])
        return result  # Stop here if inventory fails
    
    # Step 3: Process Payment via Payment Agent
    print(f"\n💳 STEP 2: PAYMENT PROCESSING")
    print("-" * 80)
    
    payment_result = process_payment(
        order_id=order_id,
        customer_id=str(order['customer_id']),
        amount=float(order['total_amount']),
        payments_df=datasets['payments']
    )
    print(f"   Result: {payment_result['message']}")
    
    if payment_result['success']:
        print(f"   ✓ Payment ID: {payment_result['payment_id']}")
        print(f"   ✓ Transaction ID: {payment_result['transaction_id']}")
        print(f"   ✓ Amount: ₹{payment_result['amount']}")
        print(f"   ✓ Method: {payment_result['method']}")
        print(f"   ✓ Status: {payment_result['status']}")
        result['payment_verified'] = True
        result['payment_id'] = payment_result['transaction_id']
    else:
        print(f"   ✗ Payment verification failed: {payment_result['status']}")
        result['errors'].append(payment_result['message'])
        return result  # Stop here if payment fails
    
    # Step 4: Start Fulfillment (only if both inventory and payment succeed)
    print(f"\n🚚 STEP 3: FULFILLMENT INITIATION")
    print("-" * 80)
    
    fulfillment_result = start_fulfillment(
        order_id=order_id,
        hold_id=result['hold_id'],
        payment_id=result['payment_id'],
        total_amount=float(order['total_amount'])
    )
    
    print(f"   Result: {fulfillment_result['message']}")
    
    if fulfillment_result['success']:
        print(f"   ✓ Fulfillment ID: {fulfillment_result['fulfillment_id']}")
        print(f"   ✓ Tracking ID: {fulfillment_result['tracking_id']}")
        print(f"   ✓ Status: {fulfillment_result['status']}")
        print(f"   ✓ Courier: {fulfillment_result['courier']}")
        print(f"   ✓ ETA: {fulfillment_result['eta']}")
        result['fulfillment_started'] = True
        result['fulfillment_id'] = fulfillment_result['fulfillment_id']
        result['tracking_id'] = fulfillment_result['tracking_id']
    else:
        print(f"   ✗ Fulfillment failed")
        result['errors'].append(fulfillment_result['message'])
        return result  # Stop if fulfillment fails
    
    # Step 5: Test Post-Purchase Return (simulating customer wants to return)
    print(f"\n📦 STEP 4: POST-PURCHASE TESTING (Return Simulation)")
    print("-" * 80)
    
    post_purchase_result = test_post_purchase_return(
        order_id=order_id,
        customer_id=int(order['customer_id']),
        order_items=items,
        datasets=datasets
    )
    
    print(f"   Result: {post_purchase_result['message']}")
    
    if post_purchase_result['success']:
        print(f"   ✓ Return ID: {post_purchase_result['return_id']}")
        print(f"   ✓ Status: {post_purchase_result['status']}")
        print(f"   ✓ Refund Amount: ₹{post_purchase_result['refund_amount']}")
        result['post_purchase_tested'] = True
        result['return_id'] = post_purchase_result['return_id']
    else:
        print(f"   ⚠ Post-purchase test failed (non-critical)")
        result['post_purchase_tested'] = False
        result['errors'].append(post_purchase_result['message'])
    
    # Step 6: Test Stylist Recommendations
    print(f"\n👔 STEP 5: STYLIST AI RECOMMENDATIONS")
    print("-" * 80)
    
    stylist_result = test_stylist_recommendations(
        customer_id=int(order['customer_id']),
        order_items=items,
        datasets=datasets
    )
    
    print(f"   Result: {stylist_result['message']}")
    
    if stylist_result['success']:
        print(f"   ✓ Purchased Product: {stylist_result.get('purchased_product', 'N/A')}")
        print(f"   ✓ AI Recommendations: {stylist_result['recommendations']} products")
        print(f"   ✓ Styling Tips: {stylist_result.get('styling_tips', 0)} tips")
        
        # Display detailed recommendations if available
        if stylist_result.get('detailed_recommendations'):
            print(f"\n   📋 DETAILED AI RECOMMENDATIONS:")
            for i, rec in enumerate(stylist_result['detailed_recommendations'][:3], 1):  # Show first 3
                print(f"      {i}. {rec.get('name', 'N/A')} (SKU: {rec.get('sku', 'N/A')})")
                print(f"         → {rec.get('reason', 'Complements your purchase')}")
        
        if stylist_result.get('styling_tips_list'):
            print(f"\n   💡 AI STYLING TIPS:")
            for i, tip in enumerate(stylist_result['styling_tips_list'][:3], 1):  # Show first 3
                print(f"      {i}. {tip}")
        
        result['stylist_tested'] = True
        result['recommendations_count'] = stylist_result['recommendations']
    else:
        print(f"   ⚠ Stylist test failed (non-critical)")
        result['stylist_tested'] = False
        result['errors'].append(stylist_result['message'])
    
    # Final Summary
    print(f"\n{'=' * 80}")
    print(f"WORKFLOW SUMMARY FOR {order_id}")
    print(f"{'=' * 80}")
    
    workflow_complete = (result['fulfillment_started'] and 
                         result.get('post_purchase_tested', False) and 
                         result.get('stylist_tested', False))
    
    result['workflow_complete'] = workflow_complete
    
    if workflow_complete:
        print(f"✓ STATUS: SUCCESS - Complete customer journey tested")
        print(f"  → Inventory: Reserved ({result['hold_id']})")
        print(f"  → Payment: Verified ({result['payment_id']})")
        print(f"  → Fulfillment: Started ({result['fulfillment_id']})")
        print(f"  → Post-Purchase: Tested ({result.get('return_id', 'N/A')})")
        print(f"  → Stylist: {result.get('recommendations_count', 0)} recommendations generated")
    else:
        print(f"✗ STATUS: PARTIAL SUCCESS - Some steps failed")
        print(f"  → Inventory: {'✓ Reserved' if result['inventory_reserved'] else '✗ Failed'}")
        print(f"  → Payment: {'✓ Verified' if result['payment_verified'] else '✗ Failed'}")
        print(f"  → Fulfillment: {'✓ Started' if result['fulfillment_started'] else '✗ Failed'}")
        print(f"  → Post-Purchase: {'✓ Tested' if result.get('post_purchase_tested', False) else '✗ Failed'}")
        print(f"  → Stylist: {'✓ Tested' if result.get('stylist_tested', False) else '✗ Failed'}")
        if result['errors']:
            print(f"\nErrors encountered:")
            for error in result['errors']:
                print(f"  • {error}")
    
    return result


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_integration_tests(num_tests: int = 5):
    """
    Run integration tests on random orders from the dataset.
    
    Args:
        num_tests: Number of random orders to test
    """
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: Complete E-Commerce Customer Journey")
    print("=" * 80)
    print(f"Testing {num_tests} random orders through all 5 agents\n")
    
    # Load datasets
    datasets = load_datasets()
    
    # Get eligible orders (those with successful payments)
    successful_payments = datasets['payments'][
        datasets['payments']['status'] == 'success'
    ]['order_id'].tolist()
    
    if len(successful_payments) < num_tests:
        print(f"⚠ Warning: Only {len(successful_payments)} orders with successful payments found.")
        num_tests = len(successful_payments)
    
    # Select random orders
    test_order_ids = random.sample(successful_payments, num_tests)
    
    print(f"Selected test orders: {', '.join(test_order_ids)}\n")
    
    # Run tests
    results = []
    for order_id in test_order_ids:
        result = test_full_order_flow(order_id, datasets)
        results.append(result)
    
    # Print final report
    print("\n\n" + "=" * 80)
    print("FINAL TEST REPORT")
    print("=" * 80)
    
    complete_success = sum(1 for r in results if r.get('workflow_complete', False))
    partial_success = sum(1 for r in results if r['fulfillment_started'] and not r.get('workflow_complete', False))
    failure_count = len(results) - complete_success - partial_success
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"✓ Complete Success (All 5 Agents): {complete_success}")
    print(f"⚠ Partial Success (Core Flow Only): {partial_success}")
    print(f"✗ Failed: {failure_count}")
    print(f"Complete Success Rate: {(complete_success / len(results) * 100):.1f}%")
    
    print("\n" + "-" * 80)
    print("DETAILED RESULTS")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.get('workflow_complete', False) else "✗"
        print(f"\n{i}. {status_icon} Order: {result['order_id']}")
        print(f"   Inventory: {'Reserved' if result['inventory_reserved'] else 'Failed'}")
        print(f"   Payment: {'Verified' if result['payment_verified'] else 'Failed'}")
        print(f"   Fulfillment: {'Started' if result['fulfillment_started'] else 'Not Started'}")
        print(f"   Post-Purchase: {'Tested' if result.get('post_purchase_tested', False) else 'Skipped'}")
        print(f"   Stylist: {'Recommendations Generated' if result.get('stylist_tested', False) else 'Skipped'}")
        
        if result['fulfillment_id']:
            print(f"   Fulfillment ID: {result['fulfillment_id']}")
            print(f"   Tracking ID: {result['tracking_id']}")
    
    print("\n" + "=" * 80)
    print("TEST EXECUTION COMPLETE")
    print("=" * 80)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                  MULTI-AGENT INTEGRATION TEST SUITE                        ║
    ║                                                                            ║
    ║  This script validates the COMPLETE CUSTOMER JOURNEY:                      ║
    ║    • Inventory Agent (port 8001) - Stock reservation                       ║
    ║    • Payment Agent (port 8003) - Payment processing                        ║
    ║    • Fulfillment Agent (port 8004) - Order shipping                        ║
    ║    • Post-Purchase Agent (port 8005) - Returns/Exchanges                   ║
    ║    • Stylist Agent (port 8006) - AI styling recommendations                ║
    ║                                                                            ║
    ║  PREREQUISITES:                                                            ║
    ║    1. All FIVE agents must be running                                      ║
    ║    2. Redis server must be running (default: localhost:6379)               ║
    ║    3. CSV datasets must exist in backend/data/ folder                      ║
    ║    4. GROQ_API_KEY must be set in .env for Stylist AI                      ║
    ║                                                                            ║
    ║  WHAT THIS TEST DOES:                                                      ║
    ║    → Reads real order data from CSV files                                  ║
    ║    → Calls Inventory Agent to reserve stock (POST /hold)                   ║
    ║    → Calls Payment Agent to process payment (POST /payment/process)        ║
    ║    → Calls Fulfillment Agent to start order processing (POST /start)       ║
    ║    → Simulates delivery and tests Post-Purchase returns                    ║
    ║    → Tests Stylist Agent for AI outfit recommendations                     ║
    ║    → Reports success/failure for each order                                ║
    ║                                                                            ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Run tests with 5 random orders
        run_integration_tests(num_tests=5)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Test execution interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
