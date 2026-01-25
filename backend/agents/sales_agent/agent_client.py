"""
Agent Client Abstraction Layer
===============================

This module provides a unified interface for calling all worker agents with:
- Mock mode for testing orchestration without running servers
- Environment-based switching (USE_REAL_AGENTS flag)
- Consistent error handling
- HTTP abstraction for all agent calls

Usage:
    # Level 1 Testing (Mock mode - no servers needed)
    export USE_REAL_AGENTS=false
    response = await call_agent("inventory", {"sku": "SKU000001"})
    
    # Level 2 Testing (Real agents)
    export USE_REAL_AGENTS=true
    response = await call_agent("inventory", {"sku": "SKU000001"})
"""

import os
import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Environment-based configuration
USE_REAL_AGENTS = os.getenv("USE_REAL_AGENTS", "false").lower() == "true"

# Worker agent URLs (configurable via environment)
AGENT_URLS = {
    "inventory": os.getenv("INVENTORY_URL", "http://localhost:8001"),
    "recommendation": os.getenv("RECOMMENDATION_URL", "http://localhost:8008"),
    "virtual_circles": os.getenv("VIRTUAL_CIRCLES_URL", "http://localhost:8007"),
    "payment": os.getenv("PAYMENT_URL", "http://localhost:8003"),
    "loyalty": os.getenv("LOYALTY_URL", "http://localhost:8002"),
    "fulfillment": os.getenv("FULFILLMENT_URL", "http://localhost:8004"),
    "post_purchase": os.getenv("POST_PURCHASE_URL", "http://localhost:8005"),
    "stylist": os.getenv("STYLIST_URL", "http://localhost:8006"),
    "ambient_commerce": os.getenv("AMBIENT_COMMERCE_URL", "http://localhost:8009"),
}

# HTTP timeout for agent calls (30s to handle LLM latency in recommendation service)
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "30"))


# ============================================================================
# MOCK RESPONSES (for Level 1 testing - orchestrator only)
# ============================================================================

def mock_inventory_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock inventory agent response."""
    sku = payload.get("sku", "SKU000001")
    location = payload.get("location", "")
    
    if location:
        return {
            "sku": sku,
            "location": location,
            "available": True,
            "quantity": 12,
            "reserved": 2,
            "in_transit": 5,
            "message": f"Mock: {sku} has 12 units at {location}"
        }
    else:
        return {
            "sku": sku,
            "online_stock": 500,
            "store_stock": {
                "STORE_MUMBAI": 182,
                "STORE_DELHI": 145,
                "STORE_BANGALORE": 203
            },
            "total_stock": 1030,
            "available": True,
            "message": f"Mock: {sku} has 1030 units total"
        }


def mock_recommendation_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock recommendation agent response."""
    mode = payload.get("mode", "normal")
    
    if mode == "gifting_genius":
        return {
            "mode": "gifting_genius",
            "recommendations": [
                {
                    "sku": "SKU000042",
                    "name": "Nike Air Max 90",
                    "price": 8999.00,
                    "reason": "Perfect gift for sneaker enthusiasts",
                    "confidence": 0.92
                },
                {
                    "sku": "SKU000123",
                    "name": "Adidas Ultraboost 22",
                    "price": 12499.00,
                    "reason": "Premium comfort gift option",
                    "confidence": 0.88
                }
            ],
            "total_results": 2,
            "message": "Mock: Gift recommendations generated"
        }
    elif mode == "trendseer":
        return {
            "mode": "trendseer",
            "trending": [
                {"sku": "SKU000067", "name": "Puma RS-X", "trend_score": 0.95},
                {"sku": "SKU000089", "name": "Reebok Classic", "trend_score": 0.87}
            ],
            "insights": "These styles are trending 40% higher this month",
            "message": "Mock: Trending products fetched"
        }
    else:
        return {
            "mode": "normal",
            "recommendations": [
                {
                    "sku": "SKU000012",
                    "name": "New Balance 574",
                    "price": 6999.00,
                    "match_score": 0.89
                }
            ],
            "message": "Mock: Standard recommendations"
        }


def mock_virtual_circles_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock virtual circles (social discovery) response."""
    return {
        "circle_insights": {
            "your_circle": "Fitness Enthusiasts",
            "circle_size": 1247,
            "common_purchases": [
                "Nike Running Shoes",
                "Puma Training Gear",
                "Adidas Sports Apparel"
            ]
        },
        "trending_in_circle": [
            {
                "sku": "SKU000156",
                "name": "Nike Air Zoom Pegasus",
                "popularity": 0.87,
                "bought_by_connections": 34
            },
            {
                "sku": "SKU000178",
                "name": "Puma Velocity Nitro",
                "popularity": 0.79,
                "bought_by_connections": 28
            }
        ],
        "message": "Mock: People like you are buying these items"
    }


def mock_payment_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock payment agent response."""
    action = payload.get("action", "process")
    
    if action == "process":
        return {
            "success": True,
            "order_id": f"ORD-MOCK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "transaction_id": "TXN-MOCK-123456",
            "amount": payload.get("amount", 9999.00),
            "status": "completed",
            "payment_method": payload.get("payment_method", "card"),
            "message": "Mock: Payment processed successfully"
        }
    elif action == "validate":
        return {
            "valid": True,
            "card_type": "VISA",
            "message": "Mock: Payment method validated"
        }
    else:
        return {
            "success": False,
            "message": "Mock: Unknown payment action"
        }


def mock_loyalty_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock loyalty agent response."""
    user_id = payload.get("user_id", "user_123")
    
    return {
        "user_id": user_id,
        "loyalty_points": 2450,
        "tier": "Gold",
        "available_coupons": [
            {
                "code": "MOCK15OFF",
                "discount": 15,
                "type": "percentage",
                "min_purchase": 5000,
                "valid_until": "2025-12-31"
            },
            {
                "code": "MOCKSAVE500",
                "discount": 500,
                "type": "fixed",
                "min_purchase": 10000,
                "valid_until": "2025-12-31"
            }
        ],
        "message": f"Mock: {user_id} has 2450 points and 2 coupons"
    }


def mock_fulfillment_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock fulfillment agent response."""
    order_id = payload.get("order_id", "ORD12345")
    
    return {
        "order_id": order_id,
        "status": "in_transit",
        "tracking_number": "MOCK-TRACK-789456",
        "estimated_delivery": "2025-12-20",
        "current_location": "Delhi Distribution Center",
        "updates": [
            {"timestamp": "2025-12-17 10:00", "status": "dispatched", "location": "Mumbai Warehouse"},
            {"timestamp": "2025-12-17 14:30", "status": "in_transit", "location": "Delhi DC"}
        ],
        "message": f"Mock: Order {order_id} is in transit"
    }


def mock_post_purchase_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock post-purchase agent response."""
    action = payload.get("action", "return")
    order_id = payload.get("order_id", "ORD12345")
    
    if action == "return":
        return {
            "request_id": f"RET-MOCK-{datetime.now().strftime('%Y%m%d')}",
            "order_id": order_id,
            "status": "approved",
            "refund_amount": 8999.00,
            "return_label": "mock-return-label-url",
            "message": "Mock: Return request approved"
        }
    elif action == "exchange":
        return {
            "request_id": f"EXG-MOCK-{datetime.now().strftime('%Y%m%d')}",
            "order_id": order_id,
            "status": "approved",
            "new_order_id": "ORD-NEW-MOCK-123",
            "message": "Mock: Exchange approved"
        }
    else:
        return {
            "success": False,
            "message": "Mock: Unknown post-purchase action"
        }


def mock_stylist_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock stylist agent response."""
    return {
        "style_recommendations": [
            {
                "outfit": "Casual Sporty",
                "items": [
                    {"sku": "SKU000034", "name": "Nike Dri-FIT T-Shirt", "category": "top"},
                    {"sku": "SKU000045", "name": "Adidas Track Pants", "category": "bottom"},
                    {"sku": "SKU000012", "name": "New Balance 574", "category": "shoes"}
                ],
                "style_score": 0.91
            }
        ],
        "message": "Mock: Stylist recommendations generated"
    }


def mock_ambient_commerce_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Mock ambient commerce (visual search) response."""
    return {
        "detected_items": [
            {
                "sku": "SKU000089",
                "name": "Reebok Classic Leather",
                "confidence": 0.94,
                "match_type": "exact"
            },
            {
                "sku": "SKU000123",
                "name": "Adidas Superstar",
                "confidence": 0.87,
                "match_type": "similar"
            }
        ],
        "total_matches": 2,
        "message": "Mock: Visual search completed"
    }


# Master mock router
def mock_agent_response(agent_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route to appropriate mock function based on agent name.
    
    Args:
        agent_name: Name of the worker agent
        payload: Request payload
        
    Returns:
        Mock response dictionary
    """
    mock_functions = {
        "inventory": mock_inventory_response,
        "recommendation": mock_recommendation_response,
        "virtual_circles": mock_virtual_circles_response,
        "payment": mock_payment_response,
        "loyalty": mock_loyalty_response,
        "fulfillment": mock_fulfillment_response,
        "post_purchase": mock_post_purchase_response,
        "stylist": mock_stylist_response,
        "ambient_commerce": mock_ambient_commerce_response,
    }
    
    mock_fn = mock_functions.get(agent_name)
    if mock_fn:
        logger.info(f"🎭 MOCK MODE: {agent_name} - returning mock data")
        return mock_fn(payload)
    else:
        logger.warning(f"⚠️ No mock function for agent: {agent_name}")
        return {"status": "ok", "message": f"Mock: {agent_name} response"}


# ============================================================================
# REAL AGENT CALLS (for Level 2/3 testing)
# ============================================================================

async def call_real_agent(agent_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make HTTP call to real worker agent.
    
    Args:
        agent_name: Name of the worker agent
        payload: Request payload
        
    Returns:
        Agent response dictionary
        
    Raises:
        Exception: On network/HTTP errors
    """
    if agent_name not in AGENT_URLS:
        raise ValueError(f"Unknown agent: {agent_name}")

    # Fulfillment has concrete REST endpoints instead of /handle
    if agent_name == "fulfillment":
        return await _call_fulfillment_agent(payload)

    url = f"{AGENT_URLS[agent_name]}/handle"

    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
            logger.info(f"🌐 REAL CALL: {agent_name} at {url}")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout calling {agent_name} after {AGENT_TIMEOUT}s")
        raise Exception(f"{agent_name} service timeout")
    except httpx.ConnectError:
        logger.error(f"🔌 Cannot connect to {agent_name} at {AGENT_URLS[agent_name]}")
        raise Exception(f"Cannot connect to {agent_name} service")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error from {agent_name}: {e.response.status_code}")
        raise Exception(f"{agent_name} service error: {e.response.status_code}")


async def _call_fulfillment_agent(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route fulfillment actions to concrete endpoints."""
    action = payload.get("action", "start")
    base = AGENT_URLS["fulfillment"]

    try:
        async with httpx.AsyncClient(timeout=AGENT_TIMEOUT) as client:
            if action == "start":
                body = {
                    "order_id": payload.get("order_id"),
                    "inventory_status": payload.get("inventory_status", "RESERVED"),
                    "payment_status": payload.get("payment_status", "SUCCESS"),
                    "amount": float(payload.get("amount", 0)),
                    "inventory_hold_id": payload.get("inventory_hold_id"),
                    "payment_transaction_id": payload.get("payment_transaction_id"),
                }
                url = f"{base}/fulfillment/start"
                logger.info(f"🌐 REAL CALL: fulfillment start at {url}")
                response = await client.post(url, json=body)

            elif action == "update_status":
                url = f"{base}/fulfillment/update-status"
                body = {
                    "order_id": payload.get("order_id"),
                    "new_status": payload.get("new_status"),
                }
                logger.info(f"🌐 REAL CALL: fulfillment update at {url}")
                response = await client.post(url, json=body)

            elif action == "mark_delivered":
                url = f"{base}/fulfillment/mark-delivered"
                body = {
                    "order_id": payload.get("order_id"),
                    "delivery_notes": payload.get("delivery_notes"),
                }
                logger.info(f"🌐 REAL CALL: fulfillment delivered at {url}")
                response = await client.post(url, json=body)

            elif action == "cancel":
                url = f"{base}/fulfillment/cancel-order"
                body = {
                    "order_id": payload.get("order_id"),
                    "reason": payload.get("reason", "Customer request"),
                    "refund_amount": float(payload.get("refund_amount", 0)),
                }
                logger.info(f"🌐 REAL CALL: fulfillment cancel at {url}")
                response = await client.post(url, json=body)

            elif action == "return":
                url = f"{base}/fulfillment/process-return"
                body = {
                    "order_id": payload.get("order_id"),
                    "reason": payload.get("reason", "Return"),
                    "refund_amount": float(payload.get("refund_amount", 0)),
                }
                logger.info(f"🌐 REAL CALL: fulfillment return at {url}")
                response = await client.post(url, json=body)

            elif action == "status":
                order_id = payload.get("order_id")
                url = f"{base}/fulfillment/{order_id}"
                logger.info(f"🌐 REAL CALL: fulfillment status at {url}")
                response = await client.get(url)

            else:
                raise ValueError(f"Unknown fulfillment action: {action}")

            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout calling fulfillment after {AGENT_TIMEOUT}s")
        raise Exception("fulfillment service timeout")
    except httpx.ConnectError:
        logger.error(f"🔌 Cannot connect to fulfillment at {base}")
        raise Exception("Cannot connect to fulfillment service")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error from fulfillment: {e.response.status_code}")
        raise Exception(f"fulfillment service error: {e.response.status_code}")


# ============================================================================
# PUBLIC API (used by LangGraph nodes)
# ============================================================================

async def call_agent(agent_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified agent call function - automatically switches between mock and real.
    
    This is the ONLY function your LangGraph nodes should call.
    
    Args:
        agent_name: Name of the worker agent
                   (inventory, recommendation, virtual_circles, payment, 
                    loyalty, fulfillment, post_purchase, stylist, ambient_commerce)
        payload: Request payload dictionary
        
    Returns:
        Response dictionary from agent (mock or real)
        
    Raises:
        Exception: Only if real agent call fails
        
    Example:
        # In your graph node
        response = await call_agent("inventory", {
            "sku": "SKU000001",
            "location": "STORE_MUMBAI"
        })
    """
    if not USE_REAL_AGENTS:
        # Level 1: Mock mode - test orchestration without servers
        return mock_agent_response(agent_name, payload)
    else:
        # Level 2/3: Real mode - call actual agent services
        return await call_real_agent(agent_name, payload)


# ============================================================================
# HEALTH CHECK UTILITIES
# ============================================================================

async def check_agent_health(agent_name: str) -> bool:
    """
    Check if a specific agent is healthy and reachable.
    
    Args:
        agent_name: Name of the worker agent
        
    Returns:
        True if agent is healthy, False otherwise
    """
    if not USE_REAL_AGENTS:
        return True  # Mock mode always "healthy"
    
    if agent_name not in AGENT_URLS:
        return False
    
    url = f"{AGENT_URLS[agent_name]}/health"
    
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(url)
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Health check failed for {agent_name}: {e}")
        return False


async def check_all_agents_health() -> Dict[str, bool]:
    """
    Check health of all configured agents.
    
    Returns:
        Dictionary mapping agent names to health status
    """
    health_status = {}
    
    for agent_name in AGENT_URLS.keys():
        health_status[agent_name] = await check_agent_health(agent_name)
    
    return health_status


# ============================================================================
# CONFIGURATION INFO
# ============================================================================

def get_agent_config() -> Dict[str, Any]:
    """
    Get current agent configuration for debugging.
    
    Returns:
        Configuration dictionary
    """
    return {
        "use_real_agents": USE_REAL_AGENTS,
        "mode": "REAL" if USE_REAL_AGENTS else "MOCK",
        "agent_urls": AGENT_URLS,
        "timeout": AGENT_TIMEOUT,
        "available_agents": list(AGENT_URLS.keys())
    }


# Log configuration on import
logger.info(f"🔧 Agent Client Config: {'REAL' if USE_REAL_AGENTS else 'MOCK'} mode")
if USE_REAL_AGENTS:
    logger.info(f"🌐 Worker agents: {list(AGENT_URLS.keys())}")
else:
    logger.info("🎭 Mock mode enabled - no servers required for testing")
