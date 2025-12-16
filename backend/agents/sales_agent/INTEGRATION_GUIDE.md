# Sales Agent ↔ Inventory Agent Integration Guide

Complete guide for connecting the Sales Agent to the Inventory Agent microservice.

## 📋 Overview

The Sales Agent orchestrates customer conversations while the Inventory Agent handles atomic stock operations. This guide shows how to integrate them.

## 🔧 Setup

### 1. Environment Variables

Already configured in `backend/.env`:

```env
# Inventory Service Configuration
INVENTORY_SERVICE_URL=http://localhost:8001
INVENTORY_TIMEOUT=5
```

### 2. Install Dependencies

```bash
cd backend/agents/sales_agent
pip install requests python-dotenv
```

## 🔌 Integration Methods

### Method 1: Using InventoryClient (Recommended)

The `inventory_client.py` module provides a clean HTTP client interface.

**Import the client:**

```python
from inventory_client import get_inventory_client, check_stock_availability

# Get client instance
client = get_inventory_client()

# Check service health
if client.health_check():
    print("✅ Inventory service connected")
```

**Common operations:**

```python
# 1. Check stock levels
stock = client.get_inventory("SKU000001")
print(f"Online stock: {stock['online_stock']}")
print(f"Total stock: {stock['total_stock']}")

# 2. Create hold during checkout
hold = client.create_hold(
    sku="SKU000001",
    quantity=2,
    location="online",
    ttl=300,  # 5 minutes
    idempotency_key=f"order-{order_id}"  # Prevent duplicates
)
print(f"Hold ID: {hold['hold_id']}")
print(f"Remaining: {hold['remaining_stock']}")

# 3. Release hold if payment fails
if payment_failed:
    result = client.release_hold(hold['hold_id'])
    print(f"Stock restored: {result['restored_stock']}")

# 4. Quick availability check
available = client.check_availability("SKU000001", quantity=5, location="online")
if available:
    print("✅ Stock available")
```

### Method 2: Direct HTTP Requests

If you prefer not to use the client wrapper:

```python
import requests
import os

INVENTORY_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8001")

# Get inventory
response = requests.get(f"{INVENTORY_URL}/inventory/SKU000001", timeout=5)
stock = response.json()

# Create hold
response = requests.post(
    f"{INVENTORY_URL}/hold",
    json={"sku": "SKU000001", "quantity": 2, "location": "online", "ttl": 300},
    headers={"X-Idempotency-Key": "order-123"},
    timeout=5
)
hold = response.json()
```

## 📝 Notebook Integration (graph.ipynb)

### Step 1: Add Imports (Cell 1)

```python
# Add after existing imports
import sys
sys.path.append('.')
from inventory_client import get_inventory_client, check_stock_availability
```

### Step 2: Initialize Client (Cell 1)

```python
# Add after Redis initialization
inventory_client = get_inventory_client()

# Check connectivity
if inventory_client.health_check():
    logger.info("✅ Inventory service connected")
else:
    logger.warning("⚠️ Inventory service unavailable (will use mock data)")
```

### Step 3: Replace Mock Functions (Cell 4)

**Before (Mock):**

```python
def check_stock_levels(sku: str) -> Dict[str, Any]:
    """Mock inventory check."""
    inventory_data = {
        "LAPTOP-001": {"available": 12, "reserved": 3, ...},
        ...
    }
    return inventory_data.get(sku, {"available": 0, ...})
```

**After (Real Inventory):**

```python
def check_stock_levels(sku: str, quantity: int = 1) -> Dict[str, Any]:
    """
    Check real-time inventory via Inventory Agent.
    Falls back to mock data if service unavailable.
    """
    try:
        # Use inventory client
        result = check_stock_availability(sku, quantity, location="online")
        
        return {
            "available": result["current_stock"],
            "in_stock": result["available"],
            "location": result["location"],
            "sku": sku
        }
    except Exception as e:
        logger.warning(f"Inventory service error: {e}, using mock data")
        
        # Fallback to mock data
        return {"available": 0, "in_stock": False, "sku": sku}
```

### Step 4: Update Worker Nodes (Cell 5)

**Handle Inventory Intent:**

```python
def handle_inventory_intent(state: SalesState) -> SalesState:
    """Handle inventory/stock inquiries."""
    message = state["messages"][-1]
    
    # Extract SKU from message
    sku_match = SKU_PATTERN.search(message)
    
    if sku_match:
        sku = sku_match.group(1)
        
        try:
            # Get real-time stock
            stock = inventory_client.get_inventory(sku)
            
            response = (
                f"📦 Stock levels for {sku}:\n"
                f"• Online: {stock['online_stock']} units\n"
                f"• Stores: {len(stock['store_stock'])} locations\n"
                f"• Total: {stock['total_stock']} units available"
            )
            
        except Exception as e:
            logger.error(f"Inventory check failed: {e}")
            response = f"I'm having trouble checking inventory for {sku} right now. Please try again."
    else:
        response = "Please provide a product SKU to check inventory (e.g., SKU000001)."
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "last_intent": "inventory"
    }
```

**Handle Order Intent (with hold creation):**

```python
def handle_order_intent(state: SalesState) -> SalesState:
    """Handle order placement with inventory holds."""
    message = state["messages"][-1]
    
    # Extract order details (SKU, quantity)
    sku_match = SKU_PATTERN.search(message)
    
    if not sku_match:
        response = "Please specify the product SKU you'd like to order."
        return {**state, "messages": state["messages"] + [response]}
    
    sku = sku_match.group(1)
    quantity = 1  # TODO: Extract from message
    
    try:
        # Check availability
        stock = inventory_client.get_inventory(sku)
        
        if stock["online_stock"] < quantity:
            response = (
                f"❌ Sorry, only {stock['online_stock']} units of {sku} available online. "
                f"Would you like to check store availability?"
            )
        else:
            # Create hold
            hold = inventory_client.create_hold(
                sku=sku,
                quantity=quantity,
                location="online",
                ttl=300,  # 5 minutes
                idempotency_key=f"session-{state.get('session_id', 'unknown')}-{sku}"
            )
            
            # Store hold_id in state for later processing
            state["hold_id"] = hold["hold_id"]
            
            response = (
                f"✅ Reserved {quantity} unit(s) of {sku} for you!\n"
                f"Your reservation expires in 5 minutes.\n"
                f"Remaining stock: {hold['remaining_stock']} units\n\n"
                f"Ready to proceed with checkout?"
            )
            
    except Exception as e:
        logger.error(f"Order processing failed: {e}")
        response = f"I'm having trouble processing your order right now. Please try again."
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "last_intent": "order"
    }
```

## 🚀 FastAPI Integration (app.py)

### Add Inventory Client to API

```python
# Add imports
from inventory_client import get_inventory_client

# Initialize client
inventory_client = get_inventory_client()

# Add health check endpoint
@app.get("/health")
async def health_check():
    """Check service health including inventory service."""
    inventory_healthy = inventory_client.health_check()
    
    return {
        "status": "healthy",
        "sales_agent": "running",
        "inventory_service": "connected" if inventory_healthy else "unavailable"
    }

# Use in message handling
@app.post("/api/message", response_model=AgentResponse)
async def handle_message(request: MessageRequest):
    """Handle message with inventory integration."""
    
    # ... existing code ...
    
    # Example: Check stock if user asks about products
    if "stock" in request.message.lower() or "available" in request.message.lower():
        try:
            stock = inventory_client.get_inventory("SKU000001")
            response_text = f"Current stock: {stock['online_stock']} units"
        except Exception as e:
            response_text = "Unable to check stock right now"
    
    # ... rest of handler ...
```

## 🧪 Testing Integration

### Test 1: Service Connectivity

```bash
cd backend/agents/sales_agent
python inventory_client.py
```

Expected output:
```
✅ Service healthy: True
✅ SKU000001 online stock: 500
✅ Hold created: hold-xxx
```

### Test 2: Notebook Integration

Run in `graph.ipynb`:

```python
# Test inventory client
from inventory_client import get_inventory_client

client = get_inventory_client()

# Check health
print(f"Healthy: {client.health_check()}")

# Get stock
stock = client.get_inventory("SKU000001")
print(f"Stock: {stock}")

# Create test hold
hold = client.create_hold("SKU000001", 1, location="online", ttl=60)
print(f"Hold ID: {hold['hold_id']}")

# Release hold
release = client.release_hold(hold['hold_id'])
print(f"Released: {release['status']}")
```

### Test 3: End-to-End Flow

1. Start both services:

```bash
# Terminal 1: Inventory Agent
cd backend/agents/worker_agents/inventory
python app.py

# Terminal 2: Sales Agent
cd backend/agents/sales_agent
python app.py
```

2. Test conversation:

```bash
curl -X POST http://localhost:8000/api/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Check stock for SKU000001"}'
```

## 📊 Error Handling

### Graceful Degradation

Always include fallbacks:

```python
def get_inventory_safe(sku: str) -> Dict[str, Any]:
    """Get inventory with fallback to mock data."""
    try:
        return inventory_client.get_inventory(sku)
    except Exception as e:
        logger.warning(f"Inventory service unavailable: {e}")
        
        # Return mock data
        return {
            "sku": sku,
            "online_stock": 0,
            "store_stock": {},
            "total_stock": 0,
            "error": "Service unavailable"
        }
```

### Retry Logic

```python
import time

def get_inventory_with_retry(sku: str, max_retries: int = 3) -> Dict[str, Any]:
    """Get inventory with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return inventory_client.get_inventory(sku)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
```

## 🔒 Production Considerations

### 1. Authentication

Add API keys to inventory service:

```python
# In inventory_client.py
INVENTORY_API_KEY = os.getenv("INVENTORY_API_KEY")

headers = {
    "X-API-Key": INVENTORY_API_KEY,
    "Content-Type": "application/json"
}
```

### 2. Circuit Breaker

Prevent cascading failures:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise
```

### 3. Caching

Cache frequent inventory lookups:

```python
from functools import lru_cache
import time

@lru_cache(maxsize=1000)
def get_cached_inventory(sku: str, timestamp: int) -> Dict[str, Any]:
    """Cache inventory for 30 seconds."""
    return inventory_client.get_inventory(sku)

# Use with current timestamp (30-second buckets)
stock = get_cached_inventory("SKU000001", int(time.time() / 30))
```

## 📂 File Structure

```
backend/agents/sales_agent/
├── app.py                      # FastAPI server
├── graph.ipynb                 # LangGraph workflow
├── inventory_client.py         # ✨ NEW: Inventory HTTP client
└── INTEGRATION_GUIDE.md        # ✨ NEW: This guide

backend/agents/worker_agents/inventory/
├── app.py                      # Inventory FastAPI server
├── redis_utils.py              # Redis operations
└── README.md                   # Inventory API docs
```

## ✅ Integration Checklist

- [x] Install requests library
- [x] Add INVENTORY_SERVICE_URL to .env
- [x] Create inventory_client.py
- [ ] Add imports to graph.ipynb (Cell 1)
- [ ] Initialize client in graph.ipynb (Cell 1)
- [ ] Replace mock check_stock_levels() (Cell 4)
- [ ] Update handle_inventory_intent() (Cell 5)
- [ ] Update handle_order_intent() with holds (Cell 5)
- [ ] Test client connectivity (python inventory_client.py)
- [ ] Test notebook integration
- [ ] Test FastAPI integration

## 🎯 Next Steps

1. **Test the client:** Run `python inventory_client.py`
2. **Update notebook:** Follow "Notebook Integration" section above
3. **Update FastAPI:** Add inventory health checks
4. **Test end-to-end:** Create order flow with holds

---

**Last Updated:** 2024-12-07  
**Version:** 1.0.0  
**Services:** Sales Agent (8000) + Inventory Agent (8001)
