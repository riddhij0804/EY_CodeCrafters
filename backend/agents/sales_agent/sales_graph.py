"""
LangGraph-based Sales Agent with Vertex AI Intent Detection

This module defines a LangGraph workflow that:
1. Detects user intent using Vertex AI
2. Routes to appropriate microservice based on intent
3. Returns structured response to frontend

Architecture:
    User Message → Intent Detection (Vertex AI) → Router → Worker Microservice → Response
"""

import logging
import os
from typing import TypedDict, Literal, Optional, List, Dict, Any
from datetime import datetime
import requests
from pathlib import Path
import pandas as pd

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# Import intent detector (absolute import for direct execution)
from vertex_intent_detector import detect_intent as vertex_detect_intent

# Load environment
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Load customer phone-to-ID mapping
_customer_phone_map = {}
_product_name_to_sku = {}
try:
    customers_csv = Path(__file__).parent.parent.parent.parent / 'backend' / 'data' / 'customers.csv'
    if customers_csv.exists():
        customers_df = pd.read_csv(customers_csv)
        _customer_phone_map = dict(zip(
            customers_df['phone_number'].astype(str), 
            customers_df['customer_id'].astype(str)
        ))
        logger.info(f"✅ Loaded {len(_customer_phone_map)} customer phone mappings")
    else:
        logger.warning("⚠️  customers.csv not found, will use fallback customer ID")
except Exception as e:
    logger.warning(f"⚠️  Could not load customer mappings: {e}")

# Load product name-to-SKU mapping
try:
    products_csv = Path(__file__).parent.parent.parent.parent / 'backend' / 'data' / 'products.csv'
    if products_csv.exists():
        products_df = pd.read_csv(products_csv)
        # Create lowercase name → SKU mapping for case-insensitive lookup
        _product_name_to_sku = dict(zip(
            products_df['ProductDisplayName'].str.lower(), 
            products_df['sku']
        ))
        logger.info(f"✅ Loaded {len(_product_name_to_sku)} product name mappings")
    else:
        logger.warning("⚠️  products.csv not found, SKU resolution will fail")
except Exception as e:
    logger.warning(f"⚠️  Could not load product mappings: {e}")

# Microservice URLs
WORKER_SERVICES = {
    "recommendation": "http://localhost:8008",  # Matches recommendation/app.py uvicorn port
    "inventory": "http://localhost:8001",
    "payment": "http://localhost:8003",
    "loyalty": "http://localhost:8002",
    "fulfillment": "http://localhost:8004",
    "post_purchase": "http://localhost:8005",
    "stylist": "http://localhost:8006",
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def resolve_product_to_sku(product_identifier: str) -> Optional[str]:
    """
    Resolve product name or SKU to actual SKU.
    
    Args:
        product_identifier: Product name or SKU
        
    Returns:
        SKU string if found, None otherwise
    """
    # If it's already a SKU format, return as-is
    if product_identifier.upper().startswith('SKU'):
        return product_identifier.upper()
    
    # Try to find by product name (case-insensitive)
    product_lower = product_identifier.lower()
    
    # Exact match first (highest priority)
    if product_lower in _product_name_to_sku:
        sku = _product_name_to_sku[product_lower]
        logger.info(f"📦 Exact match: '{product_identifier}' → {sku}")
        return sku
    
    # Partial match - collect all matches and score them
    matches = []
    search_words = set(product_lower.split())
    
    for name, sku in _product_name_to_sku.items():
        name_words = set(name.split())
        
        # Calculate match score
        if product_lower in name:
            # User query is substring of product name
            common_words = search_words & name_words
            score = len(common_words) * 2 + len(product_lower)  # Prefer more word matches
            matches.append((score, name, sku, len(name)))
        elif name in product_lower:
            # Product name is substring of user query
            common_words = search_words & name_words
            score = len(common_words) * 2
            matches.append((score, name, sku, len(name)))
    
    if matches:
        # Sort by score (desc), then by name length (asc) - prefer better matches with shorter names
        matches.sort(key=lambda x: (-x[0], x[3]))
        best_score, best_name, best_sku, _ = matches[0]
        logger.info(f"📦 Best match: '{product_identifier}' → {best_sku} ('{best_name}', score: {best_score})")
        
        # Log other candidates for debugging
        if len(matches) > 1:
            logger.debug(f"   Other matches: {[(m[1], m[2]) for m in matches[1:4]]}")
        
        return best_sku
    
    logger.warning(f"⚠️  Could not resolve '{product_identifier}' to SKU")
    return None


# ============================================================================
# STATE DEFINITION
# ============================================================================

class SalesAgentState(TypedDict):
    """
    Shared state for the sales agent workflow.
    Tracks user message, intent, routing, and responses.
    """
    # Input
    message: str
    session_token: str
    metadata: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    
    # Intent detection
    intent: str
    confidence: float
    entities: Dict[str, Any]
    intent_method: str  # "vertex_ai" or "rule_based"
    
    # Routing
    worker_service: str
    worker_url: str
    
    # Response
    response: str
    cards: List[Dict[str, Any]]
    error: Optional[str]
    
    # Metadata
    timestamp: str


# ============================================================================
# NODE 1: INTENT DETECTION (VERTEX AI)
# ============================================================================

async def detect_intent_node(state: SalesAgentState) -> SalesAgentState:
    """
    First node: Detect user intent using Vertex AI.
    
    Args:
        state: Current workflow state with user message
        
    Returns:
        Updated state with detected intent and entities
    """
    logger.info(f"🤖 Detecting intent for: '{state['message'][:100]}...'")
    
    try:
        # Call Vertex AI intent detector
        result = await vertex_detect_intent(
            user_message=state["message"],
            conversation_history=state.get("conversation_history", []),
            metadata=state.get("metadata", {})
        )
        
        # Update state with intent detection results
        state["intent"] = result["intent"]
        state["confidence"] = result["confidence"]
        state["entities"] = result["entities"]
        state["intent_method"] = result["method"]
        
        logger.info(
            f"✅ Intent: {state['intent']} "
            f"(confidence: {state['confidence']:.2f}, method: {state['intent_method']})"
        )
        logger.info(f"📦 Entities: {state['entities']}")
        
    except Exception as e:
        logger.error(f"❌ Intent detection failed: {e}")
        # Fallback to generic intent
        state["intent"] = "fallback"
        state["confidence"] = 0.5
        state["entities"] = {}
        state["intent_method"] = "error_fallback"
        state["error"] = str(e)
    
    return state


# ============================================================================
# NODE 2: ROUTER (BASED ON INTENT)
# ============================================================================

def route_by_intent(state: SalesAgentState) -> Literal[
    "recommendation_worker",
    "inventory_worker",
    "payment_worker",
    "loyalty_worker",
    "fulfillment_worker",
    "post_purchase_worker",
    "stylist_worker",
    "comparison_worker",
    "trend_worker",
    "support_worker",
    "fallback_worker"
]:
    """
    Router: Determines which worker microservice to call based on intent.
    
    Args:
        state: Current state with detected intent
        
    Returns:
        Node name to route to
    """
    intent = state["intent"]
    logger.info(f"🔀 Routing intent '{intent}' to worker...")
    
    # Intent to worker mapping
    intent_mapping = {
        "recommendation": "recommendation_worker",
        "gifting": "recommendation_worker",  # Gifting uses recommendation service
        "inventory": "inventory_worker",
        "payment": "payment_worker",
        "comparison": "recommendation_worker",  # Comparison uses recommendation
        "trend": "recommendation_worker",  # Trends use recommendation
        "support": "post_purchase_worker",  # Support uses post-purchase
        "fallback": "fallback_worker",
    }
    
    worker = intent_mapping.get(intent, "fallback_worker")
    logger.info(f"✅ Routing to: {worker}")
    
    return worker


# ============================================================================
# WORKER NODES: CALL MICROSERVICES
# ============================================================================

async def call_recommendation_worker(state: SalesAgentState) -> SalesAgentState:
    """Call recommendation microservice."""
    logger.info("📞 Calling Recommendation Worker...")
    
    state["worker_service"] = "recommendation"
    state["worker_url"] = WORKER_SERVICES["recommendation"]
    
    try:
        # Extract customer_id dynamically from phone number or metadata
        customer_id = state["metadata"].get("user_id")
        
        # If no user_id, try to resolve from phone number in session
        if not customer_id:
            phone = state["metadata"].get("phone")
            if phone and str(phone) in _customer_phone_map:
                customer_id = _customer_phone_map[str(phone)]
                logger.info(f"📞 Resolved customer ID {customer_id} from phone {phone}")
            else:
                # Fallback: use first customer from mapping if available
                customer_id = next(iter(_customer_phone_map.values())) if _customer_phone_map else "101"
                logger.warning(f"⚠️  No phone mapping found, using fallback customer ID: {customer_id}")
        
        # Build payload for recommendation API
        payload = {
            "customer_id": customer_id,
            "mode": "normal",  # Default mode
            "intent": state["entities"],
            "current_cart_skus": state["metadata"].get("cart_skus", []),
            "limit": 5
        }
        
        # Determine mode based on intent
        if state["intent"] == "gifting" or state["entities"].get("occasion") in ["birthday", "gift", "anniversary"]:
            payload["mode"] = "gifting_genius"
            payload["recipient_relation"] = state["entities"].get("recipient_relation", "friend")
            payload["recipient_gender"] = state["entities"].get("gender", "unisex")
            payload["occasion"] = state["entities"].get("occasion", "gift")
        elif state["intent"] == "trend":
            payload["mode"] = "trendseer"
        
        # Single endpoint for all modes
        endpoint = f"{state['worker_url']}/recommend"
        
        # Add budget filters if present
        if "price_max" in state["entities"]:
            if "intent" not in payload:
                payload["intent"] = {}
            payload["intent"]["budget_max"] = state["entities"]["price_max"]
        if "price_min" in state["entities"]:
            if "intent" not in payload:
                payload["intent"] = {}
            payload["intent"]["budget_min"] = state["entities"]["price_min"]
        
        # Debug logging
        logger.info(f"🔍 Recommendation payload: {payload}")
        
        # Call microservice
        response = requests.post(endpoint, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"📥 Recommendation response: {len(data.get('recommended_products', []))} products")
        
        # Format response - CHECK THE CORRECT KEY NAME
        recommendations = data.get("recommended_products", [])  # Changed from "recommendations"
        if recommendations:
            state["response"] = f"I found {len(recommendations)} great options for you! "
            state["cards"] = [
                {
                    "type": "product",
                    "sku": item.get("sku"),
                    "name": item.get("name"),
                    "price": item.get("price"),
                    "image": item.get("image_url", ""),
                    "description": item.get("personalized_reason", "")  # Use personalized_reason
                }
                for item in recommendations
            ]
        else:
            state["response"] = "I couldn't find any matches right now. Can you try different criteria?"
            state["cards"] = []
        
        logger.info(f"✅ Got {len(recommendations)} recommendations")
        
    except Exception as e:
        logger.error(f"❌ Recommendation worker failed: {e}")
        state["response"] = "I'm having trouble fetching recommendations right now. Please try again."
        state["error"] = str(e)
        state["cards"] = []
    
    return state


async def call_inventory_worker(state: SalesAgentState) -> SalesAgentState:
    """Call inventory microservice."""
    logger.info("📞 Calling Inventory Worker...")
    
    state["worker_service"] = "inventory"
    state["worker_url"] = WORKER_SERVICES["inventory"]
    
    try:
        # Get product identifier from entities (could be name or SKU)
        product_identifier = state["entities"].get("sku") or state["entities"].get("product_name")
        
        if not product_identifier:
            state["response"] = "Please tell me which product you'd like to check. You can use the product name or SKU."
            return state
        
        # Resolve product name to SKU
        sku = resolve_product_to_sku(product_identifier)
        
        if not sku:
            state["response"] = f"I couldn't find a product matching '{product_identifier}'. Could you try a different name or provide the SKU?"
            state["cards"] = []
            return state
        
        logger.info(f"🔍 Checking inventory for SKU: {sku}")
        
        # Check stock
        response = requests.get(
            f"{state['worker_url']}/inventory/{sku}",
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Response format: {sku, online_stock, store_stock, total_stock}
        total_stock = data.get("total_stock", 0)
        online_stock = data.get("online_stock", 0)
        
        if total_stock > 0:
            state["response"] = f"✅ Great news! '{product_identifier}' ({sku}) is in stock! We have {total_stock} units available ({online_stock} online)."
        else:
            state["response"] = f"❌ Sorry, '{product_identifier}' ({sku}) is currently out of stock."
        
        state["cards"] = []
        logger.info(f"✅ Stock check complete for {sku}: {total_stock} units")
        
    except Exception as e:
        logger.error(f"❌ Inventory worker failed: {e}")
        state["response"] = "I'm having trouble checking inventory right now. Please try again."
        state["error"] = str(e)
        state["cards"] = []
    
    return state


async def call_payment_worker(state: SalesAgentState) -> SalesAgentState:
    """Call payment microservice."""
    logger.info("📞 Calling Payment Worker...")
    
    state["worker_service"] = "payment"
    state["worker_url"] = WORKER_SERVICES["payment"]
    
    try:
        # Check if user wants to proceed to checkout
        state["response"] = (
            "Ready to checkout? I'll help you complete your purchase securely. "
            "Please confirm your cart and I'll guide you through payment."
        )
        state["cards"] = []
        
        logger.info("✅ Payment flow initiated")
        
    except Exception as e:
        logger.error(f"❌ Payment worker failed: {e}")
        state["response"] = "I'm having trouble with the payment service. Please try again."
        state["error"] = str(e)
        state["cards"] = []
    
    return state


async def call_fallback_worker(state: SalesAgentState) -> SalesAgentState:
    """Fallback response when intent is unclear."""
    logger.info("📞 Using fallback response...")
    
    state["worker_service"] = "fallback"
    state["worker_url"] = None
    
    state["response"] = (
        "I'm here to help! You can ask me to:\n"
        "• Show product recommendations\n"
        "• Check product availability\n"
        "• Help you checkout\n"
        "• Find gifts for someone special\n\n"
        "What would you like to do?"
    )
    state["cards"] = []
    
    return state


# ============================================================================
# BUILD THE GRAPH
# ============================================================================

def create_sales_agent_graph() -> StateGraph:
    """
    Create and configure the LangGraph sales agent workflow.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("🏗️  Building Sales Agent LangGraph...")
    
    # Initialize graph
    workflow = StateGraph(SalesAgentState)
    
    # Add nodes
    workflow.add_node("detect_intent", detect_intent_node)
    workflow.add_node("recommendation_worker", call_recommendation_worker)
    workflow.add_node("inventory_worker", call_inventory_worker)
    workflow.add_node("payment_worker", call_payment_worker)
    workflow.add_node("fallback_worker", call_fallback_worker)
    
    # Set entry point
    workflow.set_entry_point("detect_intent")
    
    # Add conditional routing after intent detection
    workflow.add_conditional_edges(
        "detect_intent",
        route_by_intent,
        {
            "recommendation_worker": "recommendation_worker",
            "inventory_worker": "inventory_worker",
            "payment_worker": "payment_worker",
            "comparison_worker": "recommendation_worker",
            "trend_worker": "recommendation_worker",
            "gifting_worker": "recommendation_worker",
            "support_worker": "fallback_worker",
            "fallback_worker": "fallback_worker",
        }
    )
    
    # All workers end the flow
    workflow.add_edge("recommendation_worker", END)
    workflow.add_edge("inventory_worker", END)
    workflow.add_edge("payment_worker", END)
    workflow.add_edge("fallback_worker", END)
    
    # Compile graph
    app = workflow.compile()
    
    logger.info("✅ Sales Agent LangGraph compiled successfully")
    
    return app


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

# Create singleton graph instance
_graph_instance = None

def get_sales_agent_graph() -> StateGraph:
    """Get or create the sales agent graph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_sales_agent_graph()
    return _graph_instance


# ============================================================================
# EXECUTION HELPER
# ============================================================================

async def process_message(
    message: str,
    session_token: str,
    metadata: Dict[str, Any] = None,
    conversation_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Process a user message through the sales agent workflow.
    
    Args:
        message: User's input message
        session_token: Session identifier
        metadata: Additional context (user_id, cart, etc.)
        conversation_history: Previous conversation turns
        
    Returns:
        Dict containing response, intent, and metadata
    """
    # Initialize state
    initial_state: SalesAgentState = {
        "message": message,
        "session_token": session_token,
        "metadata": metadata or {},
        "conversation_history": conversation_history or [],
        "intent": "",
        "confidence": 0.0,
        "entities": {},
        "intent_method": "",
        "worker_service": "",
        "worker_url": "",
        "response": "",
        "cards": [],
        "error": None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Execute graph
    graph = get_sales_agent_graph()
    final_state = await graph.ainvoke(initial_state)
    
    # Format response
    return {
        "response": final_state["response"],
        "intent": final_state["intent"],
        "confidence": final_state["confidence"],
        "entities": final_state["entities"],
        "cards": final_state["cards"],
        "method": final_state["intent_method"],
        "worker": final_state["worker_service"],
        "timestamp": final_state["timestamp"],
        "error": final_state.get("error")
    }
