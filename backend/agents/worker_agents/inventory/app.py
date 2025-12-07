# Inventory Agent - FastAPI Server
# Endpoints: GET /inventory/{sku}, POST /hold, POST /release, POST /simulate/sale

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import uuid
from datetime import datetime
import redis_utils

app = FastAPI(
    title="Inventory Agent",
    description="Redis-based inventory management with atomic operations",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class HoldRequest(BaseModel):
    sku: str = Field(..., description="Product SKU")
    quantity: int = Field(..., gt=0, description="Quantity to hold")
    location: str = Field(default="online", description="Location: 'online' or 'store:{store_id}'")
    ttl: int = Field(default=300, description="Hold duration in seconds")


class ReleaseRequest(BaseModel):
    hold_id: str = Field(..., description="Hold ID to release")


class SimulateSaleRequest(BaseModel):
    sku: str = Field(..., description="Product SKU")
    quantity: int = Field(..., gt=0, description="Quantity sold")
    location: str = Field(default="online", description="Location: 'online' or 'store:{store_id}'")


class InventoryResponse(BaseModel):
    sku: str
    online_stock: int
    store_stock: dict
    total_stock: int


class HoldResponse(BaseModel):
    hold_id: str
    sku: str
    quantity: int
    location: str
    remaining_stock: int
    expires_at: str
    status: str


class ReleaseResponse(BaseModel):
    hold_id: str
    status: str
    restored_stock: int


class SaleResponse(BaseModel):
    sku: str
    quantity_sold: int
    location: str
    remaining_stock: int
    status: str


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "Inventory Agent",
        "version": "1.0.0",
        "redis_connected": redis_utils.check_redis_health(),
        "endpoints": {
            "inventory": "GET /inventory/{sku}",
            "hold": "POST /hold",
            "release": "POST /release",
            "simulate_sale": "POST /simulate/sale"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_ok = redis_utils.check_redis_health()
    
    if not redis_ok:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    return {
        "status": "healthy",
        "redis": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }


# ==========================================
# INVENTORY ENDPOINTS
# ==========================================

@app.get("/inventory/{sku}", response_model=InventoryResponse)
async def get_inventory(sku: str):
    """
    Get stock levels for a SKU across all locations.
    
    Returns online and store-specific stock.
    """
    try:
        stock_data = redis_utils.get_stock(sku)
        
        total = stock_data["online"] + sum(stock_data["stores"].values())
        
        return InventoryResponse(
            sku=sku,
            online_stock=stock_data["online"],
            store_stock=stock_data["stores"],
            total_stock=total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inventory: {str(e)}")


@app.post("/hold", response_model=HoldResponse)
async def create_hold(
    request: HoldRequest,
    idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
):
    """
    Create an inventory hold (atomic decrement).
    
    - Atomically decrements stock
    - Creates hold with TTL
    - Supports idempotency
    
    Headers:
        X-Idempotency-Key: Optional key for idempotent requests
    """
    try:
        # Check idempotency
        if idempotency_key:
            cached_response = redis_utils.check_idempotency(idempotency_key)
            if cached_response:
                return HoldResponse(**cached_response)
        
        # Generate hold ID
        hold_id = f"hold-{uuid.uuid4()}"
        
        # Atomic stock decrement
        remaining = redis_utils.hold_stock_atomic(
            request.sku,
            request.quantity,
            request.location
        )
        
        if remaining < 0:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for {request.sku} at {request.location}"
            )
        
        # Calculate expiry time
        import time
        expiry_timestamp = time.time() + request.ttl
        expires_at = datetime.fromtimestamp(expiry_timestamp).isoformat()
        
        # Create hold with TTL
        hold_data = {
            "hold_id": hold_id,
            "sku": request.sku,
            "quantity": request.quantity,
            "location": request.location,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "status": "active"
        }
        
        redis_utils.create_hold(hold_id, hold_data, request.ttl)
        
        # Build response
        response = HoldResponse(
            hold_id=hold_id,
            sku=request.sku,
            quantity=request.quantity,
            location=request.location,
            remaining_stock=remaining,
            expires_at=expires_at,
            status="active"
        )
        
        # Save for idempotency
        if idempotency_key:
            redis_utils.save_idempotency(idempotency_key, response.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating hold: {str(e)}")


@app.post("/release", response_model=ReleaseResponse)
async def release_hold(request: ReleaseRequest):
    """
    Release an inventory hold (restore stock).
    
    - Restores stock atomically
    - Marks hold as released
    """
    try:
        # Get hold data
        hold = redis_utils.get_hold(request.hold_id)
        
        if not hold:
            raise HTTPException(
                status_code=404,
                detail=f"Hold {request.hold_id} not found or already expired"
            )
        
        # Restore stock atomically
        new_stock = redis_utils.release_stock_atomic(
            hold["sku"],
            hold["quantity"],
            hold.get("location", "online")
        )
        
        # Release hold
        redis_utils.release_hold(request.hold_id)
        
        return ReleaseResponse(
            hold_id=request.hold_id,
            status="released",
            restored_stock=new_stock
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error releasing hold: {str(e)}")


@app.post("/simulate/sale", response_model=SaleResponse)
async def simulate_sale(request: SimulateSaleRequest):
    """
    Simulate a sale by decrementing stock.
    
    For demo/testing purposes. Bypasses hold mechanism.
    """
    try:
        # Atomic stock decrement
        remaining = redis_utils.hold_stock_atomic(
            request.sku,
            request.quantity,
            request.location
        )
        
        if remaining < 0:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for {request.sku} at {request.location}"
            )
        
        return SaleResponse(
            sku=request.sku,
            quantity_sold=request.quantity,
            location=request.location,
            remaining_stock=remaining,
            status="sold"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating sale: {str(e)}")


# ==========================================
# BACKGROUND TASKS
# ==========================================

import asyncio
from contextlib import asynccontextmanager

async def cleanup_expired_holds_task():
    """Background task to cleanup expired holds every 10 seconds."""
    while True:
        try:
            expired_holds = redis_utils.get_expired_holds()
            
            for hold_id in expired_holds:
                redis_utils.cleanup_expired_hold(hold_id)
                print(f"✓ Cleaned up expired hold: {hold_id}")
            
            if expired_holds:
                print(f"✓ Cleaned up {len(expired_holds)} expired holds")
                
        except Exception as e:
            print(f"⚠ Error in cleanup task: {e}")
        
        await asyncio.sleep(10)  # Run every 10 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    print("🚀 Starting Inventory Agent...")
    print(f"✓ Redis connected: {redis_utils.check_redis_health()}")
    
    # Start background task
    cleanup_task = asyncio.create_task(cleanup_expired_holds_task())
    print("✓ Background hold cleanup task started")
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    print("👋 Inventory Agent shutting down")


app.router.lifespan_context = lifespan


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
