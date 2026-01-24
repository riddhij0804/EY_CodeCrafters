"""
Fulfillment Agent - FastAPI Server

Manages fulfillment workflows for ecommerce orders with state management,
logistics coordination, and integrations with inventory and payment agents.

Key Endpoints:
- POST /fulfillment/start
- POST /fulfillment/update-status
- POST /fulfillment/mark-delivered
- POST /fulfillment/handle-failed-delivery
- POST /fulfillment/cancel-order
- POST /fulfillment/process-return
- GET  /fulfillment/{order_id}
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uvicorn
import uuid
from datetime import datetime, timedelta
import random
import logging
import httpx
import redis_utils
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
import orders_repository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fulfillment Agent",
    description="Fulfillment management and logistics coordination system",
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

# ============================================================================
# ENUMS
# ============================================================================

class FulfillmentStatus(str, Enum):
    """Valid fulfillment statuses with enforced workflow."""
    PROCESSING = "PROCESSING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"


class CourierPartner(str, Enum):
    """Predefined courier partners."""
    FEDEX = "FedEx"
    UPS = "UPS"
    AMAZON = "Amazon Logistics"
    DHL = "DHL"
    LOCAL = "Local Courier"


class EventType(str, Enum):
    """Event types for audit trail."""
    FULFILLMENT_STARTED = "FULFILLMENT_STARTED"
    STATUS_UPDATED = "STATUS_UPDATED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    RETURN_INITIATED = "RETURN_INITIATED"
    STOCK_RELEASED = "STOCK_RELEASED"
    REFUND_INITIATED = "REFUND_INITIATED"


# ============================================================================
# DATA MODELS
# ============================================================================

class FulfillmentEvent(BaseModel):
    """Represents a single event in fulfillment timeline."""
    event_type: EventType
    timestamp: str
    details: Dict[str, Any] = Field(default_factory=dict)


class FulfillmentRecord(BaseModel):
    """Complete fulfillment record for an order."""
    fulfillment_id: str
    order_id: str
    current_status: FulfillmentStatus
    tracking_id: str
    courier_partner: CourierPartner
    eta: str  # ISO format datetime
    created_at: str
    processing_at: Optional[str] = None
    packed_at: Optional[str] = None
    shipped_at: Optional[str] = None
    out_for_delivery_at: Optional[str] = None
    delivered_at: Optional[str] = None
    cancellation_reason: Optional[str] = None
    return_reason: Optional[str] = None
    events_log: List[FulfillmentEvent] = Field(default_factory=list)
    # Integration tracking
    inventory_hold_id: Optional[str] = None  # Hold ID from inventory agent
    payment_transaction_id: Optional[str] = None  # Transaction ID from payment agent


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StartFulfillmentRequest(BaseModel):
    """Request to start fulfillment."""
    order_id: str = Field(..., description="Order ID")
    inventory_status: str = Field(..., description="Current inventory status (must be RESERVED)")
    payment_status: str = Field(..., description="Current payment status (must be SUCCESS)")
    amount: float = Field(..., description="Order amount for potential refunds")
    inventory_hold_id: Optional[str] = Field(None, description="Hold ID from inventory agent")
    payment_transaction_id: Optional[str] = Field(None, description="Transaction ID from payment agent")


class UpdateStatusRequest(BaseModel):
    """Request to update fulfillment status."""
    order_id: str = Field(..., description="Order ID")
    new_status: FulfillmentStatus = Field(..., description="Target status")


class MarkDeliveredRequest(BaseModel):
    """Request to mark order as delivered."""
    order_id: str = Field(..., description="Order ID")
    delivery_notes: Optional[str] = Field(None, description="Optional delivery notes")


class HandleFailedDeliveryRequest(BaseModel):
    """Request to handle failed delivery."""
    order_id: str = Field(..., description="Order ID")
    reason: str = Field(..., description="Reason for failure")


class HandleCancellationRequest(BaseModel):
    """Request to cancel an order."""
    order_id: str = Field(..., description="Order ID")
    reason: str = Field(..., description="Cancellation reason")
    refund_amount: float = Field(..., description="Amount to refund")


class ProcessReturnRequest(BaseModel):
    """Request to process a return."""
    order_id: str = Field(..., description="Order ID")
    reason: str = Field(..., description="Return reason")
    refund_amount: float = Field(..., description="Refund amount")


class FulfillmentResponse(BaseModel):
    """Standard response for fulfillment operations."""
    success: bool
    message: str
    fulfillment: Optional[FulfillmentRecord] = None


# ============================================================================
# REDIS STORE (Persistent fulfillment data)
# ============================================================================

# All fulfillment records are stored in Redis via redis_utils module
# In-memory store is only used within a request scope for performance
# Redis provides persistence across server restarts


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.utcnow().isoformat() + "Z"


def _generate_tracking_id() -> str:
    """Generate a unique tracking ID."""
    return f"TRK-{uuid.uuid4().hex[:12].upper()}"


def _select_courier() -> CourierPartner:
    """Randomly select a courier partner."""
    return random.choice(list(CourierPartner))


def _calculate_eta(base_days: int = 3) -> str:
    """Calculate estimated delivery time with realistic randomization.
    
    Args:
        base_days: Base number of days for delivery (default 3)
    
    Returns:
        ISO formatted datetime string
    """
    # Add random hours (0-48) to simulate distance variability
    random_hours = random.randint(0, 48)
    eta = datetime.utcnow() + timedelta(days=base_days, hours=random_hours)
    return eta.isoformat() + "Z"


def _add_event(fulfillment: FulfillmentRecord, event_type: EventType, details: Dict[str, Any]) -> None:
    """Add an event to the fulfillment's event log."""
    event = FulfillmentEvent(
        event_type=event_type,
        timestamp=_now_iso(),
        details=details
    )
    fulfillment.events_log.append(event)
    logger.info(f"Event logged for order {fulfillment.order_id}: {event_type}")


def _validate_status_transition(current: FulfillmentStatus, target: FulfillmentStatus) -> bool:
    """Validate that a status transition is allowed.
    
    Enforces strict workflow: PROCESSING → PACKED → SHIPPED → OUT_FOR_DELIVERY → DELIVERED
    
    Args:
        current: Current status
        target: Desired target status
    
    Returns:
        True if transition is valid, False otherwise
    """
    valid_transitions = {
        FulfillmentStatus.PROCESSING: [FulfillmentStatus.PACKED],
        FulfillmentStatus.PACKED: [FulfillmentStatus.SHIPPED],
        FulfillmentStatus.SHIPPED: [FulfillmentStatus.OUT_FOR_DELIVERY],
        FulfillmentStatus.OUT_FOR_DELIVERY: [FulfillmentStatus.DELIVERED],
        FulfillmentStatus.DELIVERED: [],  # Terminal state
    }
    
    allowed = valid_transitions.get(current, [])
    return target in allowed


def _update_status_timestamp(fulfillment: FulfillmentRecord, status: FulfillmentStatus) -> None:
    """Update the appropriate timestamp field based on status.
    
    Args:
        fulfillment: Fulfillment record to update
        status: New status
    """
    now = _now_iso()
    
    if status == FulfillmentStatus.PROCESSING:
        fulfillment.processing_at = now
    elif status == FulfillmentStatus.PACKED:
        fulfillment.packed_at = now
    elif status == FulfillmentStatus.SHIPPED:
        fulfillment.shipped_at = now
    elif status == FulfillmentStatus.OUT_FOR_DELIVERY:
        fulfillment.out_for_delivery_at = now
    elif status == FulfillmentStatus.DELIVERED:
        fulfillment.delivered_at = now


# ============================================================================
# EXTERNAL AGENT INTEGRATIONS (HTTP calls to respective agents)
# ============================================================================

# Configuration for external agents (update these URLs based on deployment)
INVENTORY_AGENT_URL = "http://localhost:8002"  # Inventory Agent port
PAYMENT_AGENT_URL = "http://localhost:8003"    # Payment Agent port


async def inventory_agent_release_stock(hold_id: str) -> bool:
    """Call Inventory Agent to release reserved stock via hold ID.
    
    This function makes an actual HTTP POST request to the Inventory Agent's
    /release endpoint to release a previously held inventory.
    
    Args:
        hold_id: Hold ID from the inventory agent (obtained during order placement)
    
    Returns:
        True if successful, False otherwise
    
    Raises:
        Exception on HTTP errors (logged for debugging)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{INVENTORY_AGENT_URL}/release",
                json={"hold_id": hold_id}
            )
            
            if response.status_code == 200:
                logger.info(f"Stock released successfully: hold_id={hold_id}")
                return True
            else:
                logger.error(f"Failed to release stock: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error calling inventory agent to release stock: {e}")
        return False


async def payment_agent_initiate_refund(transaction_id: str, amount: float, reason: str) -> bool:
    """Call Payment Agent to initiate a refund via transaction ID.
    
    This function makes an actual HTTP POST request to the Payment Agent's
    /payment/refund endpoint to process a refund.
    
    Args:
        transaction_id: Transaction ID from the payment agent (obtained during order payment)
        amount: Refund amount
        reason: Reason for refund (cancellation, return, etc.)
    
    Returns:
        True if successful, False otherwise
    
    Raises:
        Exception on HTTP errors (logged for debugging)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PAYMENT_AGENT_URL}/payment/refund",
                json={
                    "transaction_id": transaction_id,
                    "amount": amount,
                    "reason": reason
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Refund initiated successfully: txn_id={transaction_id}, amount={amount}")
                return True
            else:
                logger.error(f"Failed to initiate refund: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error calling payment agent to initiate refund: {e}")
        return False


# ============================================================================
# SERVICE FUNCTIONS
# ============================================================================

def start_fulfillment(request: StartFulfillmentRequest) -> FulfillmentRecord:
    """Start fulfillment for an order.
    
    Validates that:
    - Order hasn't been processed already (idempotency)
    - Inventory status is RESERVED
    - Payment status is SUCCESS
    
    Args:
        request: StartFulfillmentRequest with order and status info
    
    Returns:
        Created FulfillmentRecord
    
    Raises:
        HTTPException if validation fails
    """
    # Check if order already has fulfillment (prevent duplicates)
    if redis_utils.order_exists(request.order_id):
        logger.warning(f"Fulfillment already exists for order {request.order_id}")
        raise HTTPException(
            status_code=409,
            detail=f"Fulfillment already started for order {request.order_id}"
        )
    
    # Validate inventory status
    if request.inventory_status != "RESERVED":
        logger.error(f"Invalid inventory status for order {request.order_id}: {request.inventory_status}")
        raise HTTPException(
            status_code=400,
            detail=f"Inventory status must be RESERVED, got {request.inventory_status}"
        )
    
    # Validate payment status
    if request.payment_status != "SUCCESS":
        logger.error(f"Invalid payment status for order {request.order_id}: {request.payment_status}")
        raise HTTPException(
            status_code=400,
            detail=f"Payment status must be SUCCESS, got {request.payment_status}"
        )
    
    # Create new fulfillment record
    now = _now_iso()
    fulfillment = FulfillmentRecord(
        fulfillment_id=str(uuid.uuid4()),
        order_id=request.order_id,
        current_status=FulfillmentStatus.PROCESSING,
        tracking_id=_generate_tracking_id(),
        courier_partner=_select_courier(),
        eta=_calculate_eta(),
        created_at=now,
        processing_at=now,
        inventory_hold_id=request.inventory_hold_id,  # Store hold ID from inventory agent
        payment_transaction_id=request.payment_transaction_id,  # Store transaction ID from payment agent
    )
    
    # Log initial event
    redis_utils.add_fulfillment_event(request.order_id, {
        "event_type": EventType.FULFILLMENT_STARTED.value,
        "timestamp": _now_iso(),
        "details": {
            "tracking_id": fulfillment.tracking_id,
            "courier_partner": fulfillment.courier_partner,
            "eta": fulfillment.eta,
            "inventory_hold_id": request.inventory_hold_id,
            "payment_transaction_id": request.payment_transaction_id
        }
    })
    
    # Store in Redis
    redis_utils.store_fulfillment(request.order_id, fulfillment.dict())
    
    logger.info(f"Fulfillment started for order {request.order_id}: {fulfillment.fulfillment_id}")
    return fulfillment


def update_status(request: UpdateStatusRequest) -> FulfillmentRecord:
    """Update fulfillment status with strict transition rules.
    
    Args:
        request: UpdateStatusRequest with order_id and new_status
    
    Returns:
        Updated FulfillmentRecord
    
    Raises:
        HTTPException if order not found or transition invalid
    """
    # Retrieve fulfillment from Redis
    fulfillment_data = redis_utils.get_fulfillment(request.order_id)
    if not fulfillment_data:
        logger.error(f"Fulfillment not found for order {request.order_id}")
        raise HTTPException(status_code=404, detail=f"Fulfillment not found for order {request.order_id}")
    
    # Convert Redis dict to FulfillmentRecord object
    fulfillment = FulfillmentRecord(**fulfillment_data)
    
    # Validate transition
    if not _validate_status_transition(fulfillment.current_status, request.new_status):
        logger.error(f"Invalid transition for order {request.order_id}: {fulfillment.current_status} → {request.new_status}")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {fulfillment.current_status} to {request.new_status}"
        )
    
    # Update status
    old_status = fulfillment.current_status
    fulfillment.current_status = request.new_status
    _update_status_timestamp(fulfillment, request.new_status)
    
    # Save updated fulfillment to Redis
    redis_utils.store_fulfillment(request.order_id, fulfillment.dict())
    
    # Log event
    redis_utils.add_fulfillment_event(request.order_id, {
        "event_type": "STATUS_UPDATED",
        "timestamp": _now_iso(),
        "details": {
            "from_status": str(old_status),
            "to_status": str(request.new_status)
        }
    })
    
    logger.info(f"Status updated for order {request.order_id}: {old_status} → {request.new_status}")
    return fulfillment


def mark_delivered(request: MarkDeliveredRequest) -> FulfillmentRecord:
    """Mark an order as delivered.
    
    This is a convenience endpoint that validates the order is OUT_FOR_DELIVERY
    and transitions to DELIVERED.
    
    Args:
        request: MarkDeliveredRequest with order_id and optional notes
    
    Returns:
        Updated FulfillmentRecord
    
    Raises:
        HTTPException if order not found or not ready for delivery
    """
    # Retrieve from Redis
    fulfillment_data = redis_utils.get_fulfillment(request.order_id)
    if not fulfillment_data:
        logger.error(f"Fulfillment not found for order {request.order_id}")
        raise HTTPException(status_code=404, detail=f"Fulfillment not found for order {request.order_id}")
    
    fulfillment = FulfillmentRecord(**fulfillment_data)
    
    # Can only deliver if currently out for delivery
    if fulfillment.current_status != FulfillmentStatus.OUT_FOR_DELIVERY:
        logger.error(f"Order {request.order_id} not out for delivery yet: {fulfillment.current_status}")
        raise HTTPException(
            status_code=400,
            detail=f"Order must be OUT_FOR_DELIVERY to mark as delivered, current status: {fulfillment.current_status}"
        )
    
    # Update status
    fulfillment.current_status = FulfillmentStatus.DELIVERED
    fulfillment.delivered_at = _now_iso()
    
    # Save to Redis
    redis_utils.store_fulfillment(request.order_id, fulfillment.dict())
    
    # Log event
    redis_utils.add_fulfillment_event(request.order_id, {
        "event_type": "STATUS_UPDATED",
        "timestamp": _now_iso(),
        "details": {
            "from_status": str(FulfillmentStatus.OUT_FOR_DELIVERY),
            "to_status": str(FulfillmentStatus.DELIVERED),
            "delivery_notes": request.delivery_notes
        }
    })
    
    logger.info(f"Order {request.order_id} marked as delivered")
    return fulfillment


async def handle_failed_delivery(request: HandleFailedDeliveryRequest) -> FulfillmentRecord:
    """Handle a failed delivery attempt.
    
    Logs the failure but does not change status (order remains OUT_FOR_DELIVERY).
    
    Args:
        request: HandleFailedDeliveryRequest with order_id and reason
    
    Returns:
        Updated FulfillmentRecord
    
    Raises:
        HTTPException if order not found
    """
    # Retrieve from Redis
    fulfillment_data = redis_utils.get_fulfillment(request.order_id)
    if not fulfillment_data:
        logger.error(f"Fulfillment not found for order {request.order_id}")
        raise HTTPException(status_code=404, detail=f"Fulfillment not found for order {request.order_id}")
    
    fulfillment = FulfillmentRecord(**fulfillment_data)
    
    # Log the failure event
    redis_utils.add_fulfillment_event(request.order_id, {
        "event_type": "DELIVERY_FAILED",
        "timestamp": _now_iso(),
        "details": {
            "reason": request.reason,
            "current_status": str(fulfillment.current_status)
        }
    })
    
    logger.warning(f"Delivery failed for order {request.order_id}: {request.reason}")
    return fulfillment


async def handle_order_cancellation(request: HandleCancellationRequest) -> FulfillmentRecord:
    """Cancel an order and release stock + initiate refund.
    
    Calls external agents to:
    - Release reserved stock
    - Initiate payment refund
    
    Args:
        request: HandleCancellationRequest with order info and refund amount
    
    Returns:
        Updated FulfillmentRecord
    
    Raises:
        HTTPException if order not found or already delivered
    """
    # Retrieve from Redis
    fulfillment_data = redis_utils.get_fulfillment(request.order_id)
    if not fulfillment_data:
        logger.error(f"Fulfillment not found for order {request.order_id}")
        raise HTTPException(status_code=404, detail=f"Fulfillment not found for order {request.order_id}")
    
    fulfillment = FulfillmentRecord(**fulfillment_data)
    
    # Cannot cancel if already delivered
    if fulfillment.current_status == FulfillmentStatus.DELIVERED:
        logger.error(f"Cannot cancel delivered order {request.order_id}")
        raise HTTPException(status_code=400, detail="Cannot cancel an order that has already been delivered")
    
    # Record cancellation reason
    fulfillment.cancellation_reason = request.reason
    
    # Call inventory agent to release stock (using hold_id stored during start)
    if fulfillment.inventory_hold_id:
        try:
            stock_released = await inventory_agent_release_stock(fulfillment.inventory_hold_id)
            if stock_released:
                redis_utils.add_fulfillment_event(request.order_id, {
                    "event_type": EventType.STOCK_RELEASED.value,
                    "timestamp": _now_iso(),
                    "details": {"reason": "Cancellation"}
                })
                logger.info(f"Stock released for cancelled order {request.order_id}")
        except Exception as e:
            logger.error(f"Failed to release stock for order {request.order_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to release stock")
    else:
        logger.warning(f"No inventory hold ID found for order {request.order_id}")
    
    # Call payment agent to initiate refund (using transaction_id stored during start)
    if fulfillment.payment_transaction_id:
        try:
            refund_initiated = await payment_agent_initiate_refund(
                fulfillment.payment_transaction_id,
                request.refund_amount,
                "Order Cancellation"
            )
            if refund_initiated:
                redis_utils.add_fulfillment_event(request.order_id, {
                    "event_type": EventType.REFUND_INITIATED.value,
                    "timestamp": _now_iso(),
                    "details": {
                        "amount": request.refund_amount,
                        "reason": "Cancellation"
                    }
                })
                logger.info(f"Refund initiated for cancelled order {request.order_id}: ${request.refund_amount}")
        except Exception as e:
            logger.error(f"Failed to initiate refund for order {request.order_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to initiate refund")
    else:
        logger.warning(f"No payment transaction ID found for order {request.order_id}")
    
    # Log cancellation event and save to Redis
    redis_utils.add_fulfillment_event(request.order_id, {
        "event_type": EventType.ORDER_CANCELLED.value,
        "timestamp": _now_iso(),
        "details": {
            "reason": request.reason,
            "refund_amount": request.refund_amount
        }
    })
    redis_utils.store_fulfillment(request.order_id, fulfillment.dict())
    
    logger.info(f"Order {request.order_id} cancelled successfully")
    return fulfillment


async def process_return(request: ProcessReturnRequest) -> FulfillmentRecord:
    """Process a return after delivery.
    
    Calls external agents to:
    - Release stock back to inventory
    - Initiate payment refund
    
    Args:
        request: ProcessReturnRequest with order and refund info
    
    Returns:
        Updated FulfillmentRecord
    
    Raises:
        HTTPException if order not found or not delivered
    """
    # Retrieve from Redis
    fulfillment_data = redis_utils.get_fulfillment(request.order_id)
    if not fulfillment_data:
        logger.error(f"Fulfillment not found for order {request.order_id}")
        raise HTTPException(status_code=404, detail=f"Fulfillment not found for order {request.order_id}")
    
    fulfillment = FulfillmentRecord(**fulfillment_data)
    
    # Can only return if delivered
    if fulfillment.current_status != FulfillmentStatus.DELIVERED:
        logger.error(f"Cannot return non-delivered order {request.order_id}: {fulfillment.current_status}")
        raise HTTPException(
            status_code=400,
            detail=f"Can only return delivered orders, current status: {fulfillment.current_status}"
        )
    
    # Record return reason
    fulfillment.return_reason = request.reason
    
    # Call inventory agent to release stock (using hold_id stored during start)
    if fulfillment.inventory_hold_id:
        try:
            stock_released = await inventory_agent_release_stock(fulfillment.inventory_hold_id)
            if stock_released:
                redis_utils.add_fulfillment_event(request.order_id, {
                    "event_type": EventType.STOCK_RELEASED.value,
                    "timestamp": _now_iso(),
                    "details": {"reason": "Return"}
                })
                logger.info(f"Stock released for returned order {request.order_id}")
        except Exception as e:
            logger.error(f"Failed to release stock for returned order {request.order_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to release stock")
    else:
        logger.warning(f"No inventory hold ID found for order {request.order_id}")
    
    # Call payment agent to initiate refund (using transaction_id stored during start)
    if fulfillment.payment_transaction_id:
        try:
            refund_initiated = await payment_agent_initiate_refund(
                fulfillment.payment_transaction_id,
                request.refund_amount,
                "Order Return"
            )
            if refund_initiated:
                redis_utils.add_fulfillment_event(request.order_id, {
                    "event_type": EventType.REFUND_INITIATED.value,
                    "timestamp": _now_iso(),
                    "details": {
                        "amount": request.refund_amount,
                        "reason": "Return"
                    }
                })
                logger.info(f"Refund initiated for returned order {request.order_id}: ${request.refund_amount}")
        except Exception as e:
            logger.error(f"Failed to initiate refund for returned order {request.order_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to initiate refund")
    else:
        logger.warning(f"No payment transaction ID found for order {request.order_id}")
    
    # Log return event and save to Redis
    redis_utils.add_fulfillment_event(request.order_id, {
        "event_type": EventType.RETURN_INITIATED.value,
        "timestamp": _now_iso(),
        "details": {
            "reason": request.reason,
            "refund_amount": request.refund_amount
        }
    })
    redis_utils.store_fulfillment(request.order_id, fulfillment.dict())
    
    logger.info(f"Return processed for order {request.order_id}")
    return fulfillment


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/fulfillment/start", response_model=FulfillmentResponse)
async def api_start_fulfillment(request: StartFulfillmentRequest):
    """Start fulfillment for an order.
    
    Validates inventory_status == "RESERVED" and payment_status == "SUCCESS"
    before creating fulfillment record with tracking ID, courier, and ETA.
    """
    try:
        fulfillment = start_fulfillment(request)
        return FulfillmentResponse(
            success=True,
            message="Fulfillment started successfully",
            fulfillment=fulfillment
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error starting fulfillment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/fulfillment/update-status", response_model=FulfillmentResponse)
async def api_update_status(request: UpdateStatusRequest):
    """Update fulfillment status with enforced transition rules.
    
    Only allows transitions following: PROCESSING → PACKED → SHIPPED → OUT_FOR_DELIVERY → DELIVERED
    """
    try:
        fulfillment = update_status(request)
        return FulfillmentResponse(
            success=True,
            message=f"Status updated to {request.new_status}",
            fulfillment=fulfillment
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error updating status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/fulfillment/mark-delivered", response_model=FulfillmentResponse)
async def api_mark_delivered(request: MarkDeliveredRequest):
    """Mark an order as delivered.
    
    Validates order is OUT_FOR_DELIVERY before transitioning to DELIVERED.
    """
    try:
        fulfillment = mark_delivered(request)
        return FulfillmentResponse(
            success=True,
            message="Order marked as delivered",
            fulfillment=fulfillment
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error marking delivered: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/fulfillment/handle-failed-delivery", response_model=FulfillmentResponse)
async def api_handle_failed_delivery(request: HandleFailedDeliveryRequest):
    """Handle a failed delivery attempt.
    
    Logs the failure event without changing status.
    """
    try:
        fulfillment = await handle_failed_delivery(request)
        return FulfillmentResponse(
            success=True,
            message="Failed delivery recorded",
            fulfillment=fulfillment
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error handling failed delivery: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/fulfillment/cancel-order", response_model=FulfillmentResponse)
async def api_cancel_order(request: HandleCancellationRequest):
    """Cancel an order and process refund.
    
    Calls inventory_agent.release_stock() and payment_agent.initiate_refund().
    Cannot cancel if already delivered.
    """
    try:
        fulfillment = await handle_order_cancellation(request)
        return FulfillmentResponse(
            success=True,
            message="Order cancelled successfully",
            fulfillment=fulfillment
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error cancelling order: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/fulfillment/process-return", response_model=FulfillmentResponse)
async def api_process_return(request: ProcessReturnRequest):
    """Process a return after delivery.
    
    Calls inventory_agent.release_stock() and payment_agent.initiate_refund().
    Only allowed for delivered orders.
    """
    try:
        fulfillment = await process_return(request)
        return FulfillmentResponse(
            success=True,
            message="Return processed successfully",
            fulfillment=fulfillment
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error processing return: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/fulfillment/{order_id}", response_model=FulfillmentResponse)
async def api_get_fulfillment(order_id: str):
    """Retrieve fulfillment record for an order."""
    fulfillment_data = redis_utils.get_fulfillment(order_id)
    if not fulfillment_data:
        # Fallback: Check if order exists in orders.csv via orders_repository
        logger.error(f"📦 Order {order_id} not in Redis, checking orders.csv...")
        try:
            import csv
            from pathlib import Path
            
            # Check orders.csv directly
            orders_file = Path(__file__).parent.parent.parent.parent / "data" / "orders.csv"
            logger.error(f"   Checking file: {orders_file}")
            logger.error(f"   File exists: {orders_file.exists()}")
            
            if orders_file.exists():
                with open(orders_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row and row.get('order_id', '').strip() == order_id:
                            logger.error(f"✅ FOUND order in CSV: {order_id}")
                            
                            # Map order status to fulfillment status
                            order_status = row.get('status', 'placed').lower()
                            status_map = {
                                'placed': FulfillmentStatus.PROCESSING,
                                'confirmed': FulfillmentStatus.PROCESSING,
                                'processing': FulfillmentStatus.PROCESSING,
                                'packed': FulfillmentStatus.PACKED,
                                'shipped': FulfillmentStatus.SHIPPED,
                                'out_for_delivery': FulfillmentStatus.OUT_FOR_DELIVERY,
                                'delivered': FulfillmentStatus.DELIVERED,
                                'cancelled': FulfillmentStatus.CANCELLED,
                                'returned': FulfillmentStatus.RETURNED
                            }
                            fulfillment_status = status_map.get(order_status, FulfillmentStatus.PROCESSING)
                            
                            # Use actual created_at from CSV or current time
                            created_at = row.get('created_at', datetime.utcnow().isoformat())
                            
                            # Calculate ETA based on status
                            if fulfillment_status == FulfillmentStatus.DELIVERED:
                                eta = created_at  # Already delivered
                            elif fulfillment_status in [FulfillmentStatus.CANCELLED, FulfillmentStatus.RETURNED]:
                                eta = created_at  # No ETA for cancelled/returned
                            elif fulfillment_status == FulfillmentStatus.SHIPPED:
                                eta = (datetime.utcnow() + timedelta(days=1)).isoformat()
                            else:
                                eta = (datetime.utcnow() + timedelta(days=3)).isoformat()
                            
                            synthetic = {
                                'fulfillment_id': f'FUL-{order_id}-001',
                                'order_id': order_id,
                                'current_status': fulfillment_status,
                                'tracking_id': f'TRK-{order_id}',
                                'courier_partner': CourierPartner.LOCAL,
                                'eta': eta,
                                'created_at': created_at
                            }
                            fulfillment = FulfillmentRecord(**synthetic)
                            logger.error(f"   Returning fulfillment with status: {fulfillment_status}")
                            return FulfillmentResponse(
                                success=True,
                                message=f"Order {order_status}",
                                fulfillment=fulfillment
                            )
                logger.error(f"   Order NOT found after scanning CSV")
            else:
                logger.error(f"   CSV file not found at {orders_file}")
                
        except Exception as e:
            logger.error(f"❌ Exception: {type(e).__name__}: {e}", exc_info=True)
        
        logger.error(f"   Raising 404")
        raise HTTPException(status_code=404, detail=f"Fulfillment not found for order {order_id}")
    
    fulfillment = FulfillmentRecord(**fulfillment_data)
    return FulfillmentResponse(
        success=True,
        message="Fulfillment retrieved successfully",
        fulfillment=fulfillment
    )


@app.get("/fulfillment-status/{order_id}")
async def api_get_status(order_id: str):
    """Get current fulfillment status for an order."""
    fulfillment_data = redis_utils.get_fulfillment(order_id)
    if not fulfillment_data:
        raise HTTPException(status_code=404, detail=f"Fulfillment not found for order {order_id}")
    
    fulfillment = FulfillmentRecord(**fulfillment_data)
    
    return {
        "order_id": order_id,
        "current_status": fulfillment.current_status,
        "tracking_id": fulfillment.tracking_id,
        "courier_partner": fulfillment.courier_partner,
        "eta": fulfillment.eta
    }


@app.get("/")
async def health_check():
    """Health check endpoint."""
    redis_ok = redis_utils.check_redis_health()
    
    if not redis_ok:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    return {
        "status": "running",
        "service": "Fulfillment Agent",
        "version": "1.0.0",
        "redis": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
