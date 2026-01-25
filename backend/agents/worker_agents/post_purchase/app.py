"""
Post-Purchase Support Agent - FastAPI Server
Handles returns, exchanges, and complaints

Endpoints:
- POST /post-purchase/return
- POST /post-purchase/exchange
- POST /post-purchase/complaint
- GET /post-purchase/return-reasons
- GET /post-purchase/returns/{user_id}
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import uvicorn
import uuid
from datetime import datetime
import redis_utils

app = FastAPI(
    title="Post-Purchase Support Agent",
    description="Handles returns, exchanges, and customer complaints",
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

class ReturnRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    order_id: str = Field(..., description="Order ID to return")
    product_sku: str = Field(..., description="Product SKU")
    reason_code: str = Field(..., description="Return reason code")
    additional_comments: Optional[str] = Field(None, description="Additional comments")
    images: Optional[List[str]] = Field(default_factory=list, description="Image URLs if any")


class ExchangeRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    order_id: str = Field(..., description="Order ID")
    product_sku: str = Field(..., description="Product SKU to exchange")
    current_size: str = Field(..., description="Current size")
    requested_size: str = Field(..., description="Requested new size")
    reason: Optional[str] = Field(None, description="Reason for exchange")


class ComplaintRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    order_id: Optional[str] = Field(None, description="Related order ID (optional)")
    issue_type: str = Field(..., description="Type of issue")
    description: str = Field(..., description="Issue description")
    priority: Optional[str] = Field("medium", description="Priority: low, medium, high")


class ReturnResponse(BaseModel):
    success: bool
    return_id: str
    status: str
    message: str
    pickup_date: Optional[str]
    refund_amount: Optional[float]
    timestamp: str


class ExchangeResponse(BaseModel):
    success: bool
    exchange_id: str
    status: str
    message: str
    new_product_sku: str
    delivery_date: Optional[str]
    timestamp: str


class ComplaintResponse(BaseModel):
    success: bool
    complaint_id: str
    status: str
    ticket_number: str
    message: str
    timestamp: str


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    order_id: Optional[str] = Field(None, description="Related order ID (optional)")
    product_sku: str = Field(..., description="Product SKU")
    size_purchased: Optional[str] = Field(None, description="Purchased size")
    fit_rating: Optional[str] = Field("perfect", description="Fit rating feedback")
    length_feedback: Optional[str] = Field("not_specified", description="Length feedback")
    comments: Optional[str] = Field(None, description="Additional comments")


class FeedbackResponse(BaseModel):
    success: bool
    feedback_id: str
    status: str
    message: str
    timestamp: str


class OrderItem(BaseModel):
    sku: str = Field(..., description="Product SKU")
    name: Optional[str] = Field(None, description="Product name")
    brand: Optional[str] = Field(None, description="Product brand")
    category: Optional[str] = Field(None, description="Product category")
    quantity: int = Field(1, ge=1, description="Quantity purchased")
    unit_price: float = Field(..., ge=0, description="Unit price")
    line_total: float = Field(..., ge=0, description="Line total")


class RegisterOrderRequest(BaseModel):
    order_id: str = Field(..., description="Unique order identifier")
    user_id: str = Field(..., description="Customer identifier")
    amount: float = Field(..., ge=0, description="Total order amount")
    items: List[OrderItem] = Field(..., description="Purchased items")
    status: Optional[str] = Field("completed", description="Order status")
    created_at: Optional[str] = Field(None, description="Order timestamp")
    shipping_address: Optional[Dict[str, str]] = Field(None, description="Delivery address")
    metadata: Optional[Dict[str, str]] = Field(None, description="Additional metadata")


# ==========================================
# RETURN REASONS DATABASE
# ==========================================

RETURN_REASONS = {
    "SIZE_ISSUE": {
        "code": "SIZE_ISSUE",
        "label": "Size doesn't fit",
        "description": "Product size is too small or too large",
        "requires_pickup": True
    },
    "QUALITY_ISSUE": {
        "code": "QUALITY_ISSUE",
        "label": "Quality issue / Defective",
        "description": "Product has quality defects or damage",
        "requires_pickup": True
    },
    "WRONG_ITEM": {
        "code": "WRONG_ITEM",
        "label": "Wrong item received",
        "description": "Received different product than ordered",
        "requires_pickup": True
    },
    "NOT_AS_DESCRIBED": {
        "code": "NOT_AS_DESCRIBED",
        "label": "Not as described",
        "description": "Product doesn't match description/images",
        "requires_pickup": True
    },
    "CHANGED_MIND": {
        "code": "CHANGED_MIND",
        "label": "Changed my mind",
        "description": "No longer need the product",
        "requires_pickup": True
    },
    "DUPLICATE_ORDER": {
        "code": "DUPLICATE_ORDER",
        "label": "Ordered by mistake / Duplicate",
        "description": "Accidentally ordered multiple times",
        "requires_pickup": True
    },
    "FOUND_BETTER_PRICE": {
        "code": "FOUND_BETTER_PRICE",
        "label": "Found better price elsewhere",
        "description": "Product available at lower price",
        "requires_pickup": True
    },
    "LATE_DELIVERY": {
        "code": "LATE_DELIVERY",
        "label": "Delivery was too late",
        "description": "Product arrived after needed date",
        "requires_pickup": True
    },
    "DAMAGED_IN_SHIPPING": {
        "code": "DAMAGED_IN_SHIPPING",
        "label": "Damaged during shipping",
        "description": "Product damaged in transit",
        "requires_pickup": True
    },
    "NOT_SATISFIED": {
        "code": "NOT_SATISFIED",
        "label": "Not satisfied with product",
        "description": "Product didn't meet expectations",
        "requires_pickup": True
    }
}

ISSUE_TYPES = [
    "delivery_issue",
    "payment_issue",
    "product_quality",
    "customer_service",
    "website_issue",
    "account_issue",
    "other"
]


# ==========================================
# ROUTES
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Post-Purchase Support Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/post-purchase/return-reasons")
async def get_return_reasons():
    """Get list of all return reasons"""
    return {
        "return_reasons": list(RETURN_REASONS.values()),
        "total_reasons": len(RETURN_REASONS)
    }


@app.post("/post-purchase/return", response_model=ReturnResponse)
async def process_return(request: ReturnRequest):
    """
    Process return request
    Uses real orders from orders.csv
    
    Steps:
    1. Validate reason code
    2. Check order from orders.csv
    3. Generate return ID
    4. Schedule pickup
    5. Initiate refund process
    """
    try:
        # Step 1: Validate return reason
        if request.reason_code not in RETURN_REASONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid return reason. Valid codes: {list(RETURN_REASONS.keys())}"
            )
        
        reason_info = RETURN_REASONS[request.reason_code]
        
        # Step 1.5: Verify order exists in orders.csv
        order = redis_utils.get_order_details(request.order_id)
        order_verified = bool(order)

        if not order:
            # Fall back to minimal order context so returns still proceed
            order = {
                'order_id': request.order_id,
                'customer_id': request.user_id,
                'items': [{
                    'sku': request.product_sku,
                    'name': '',
                    'brand': '',
                    'category': '',
                    'quantity': 1,
                    'unit_price': 0,
                    'line_total': 0,
                }],
                'total_amount': 0,
                'status': 'completed',
                'created_at': datetime.now().isoformat(),
            }

        # Verify user owns this order when the record exists
        if order_verified and order['customer_id'] != request.user_id:
            raise HTTPException(status_code=403, detail="Order does not belong to this user")

        # Verify product in order when we have order data; otherwise accept
        product_found = any(item['sku'] == request.product_sku for item in order['items']) if order_verified else True
        if order_verified and not product_found:
            raise HTTPException(status_code=404, detail="Product not found in this order")
        
        # Step 2: Generate return ID
        return_id = f"RET_{uuid.uuid4().hex[:12].upper()}"
        
        # Step 3: Calculate pickup date (2 days from now)
        from datetime import timedelta
        pickup_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        # Step 4: Store return request
        return_data = {
            "return_id": return_id,
            "user_id": request.user_id,
            "order_id": request.order_id,
            "product_sku": request.product_sku,
            "reason_code": request.reason_code,
            "reason_label": reason_info["label"],
            "additional_comments": request.additional_comments or "",
            "status": "initiated",
            "pickup_date": pickup_date,
            "timestamp": datetime.now().isoformat(),
            "refund_status": "pending",
            "order_verified": order_verified
        }
        
        redis_utils.store_return_request(return_id, return_data)
        
        # Step 5: Return response
        return ReturnResponse(
            success=True,
            return_id=return_id,
            status="initiated",
            message=(
                f"Return request created. Reason: {reason_info['label']}. Pickup scheduled for {pickup_date}."
                if order_verified else
                f"Return request received for order {request.order_id}. We will verify purchase details and schedule pickup for {pickup_date}."
            ),
            pickup_date=pickup_date,
            refund_amount=None,  # Will be calculated after item received
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-purchase/exchange", response_model=ExchangeResponse)
async def process_exchange(request: ExchangeRequest):
    """
    Process exchange request (same product, different size)
    Uses real orders from orders.csv
    
    Steps:
    1. Verify order from orders.csv
    2. Validate size availability
    3. Generate exchange ID
    4. Create new order for different size
    5. Schedule pickup of old item
    """
    try:
        # Step 1: Verify order exists in orders.csv
        order = redis_utils.get_order_details(request.order_id)
        order_verified = bool(order)

        if not order:
            order = {
                'order_id': request.order_id,
                'customer_id': request.user_id,
                'items': [{
                    'sku': request.product_sku,
                    'name': '',
                    'brand': '',
                    'category': '',
                    'quantity': 1,
                    'unit_price': 0,
                    'line_total': 0,
                }],
                'total_amount': 0,
                'status': 'completed',
                'created_at': datetime.now().isoformat(),
            }

        # Verify user owns this order when available
        if order_verified and order['customer_id'] != request.user_id:
            raise HTTPException(status_code=403, detail="Order does not belong to this user")

        # Verify product belongs to order when we have order details; otherwise accept
        product_found = any(item['sku'] == request.product_sku for item in order['items']) if order_verified else True
        if order_verified and not product_found:
            raise HTTPException(status_code=404, detail="Product not found in this order")
        
        # Generate exchange ID
        exchange_id = f"EXC_{uuid.uuid4().hex[:12].upper()}"
        
        # Calculate delivery date
        from datetime import timedelta
        delivery_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        
        # Store exchange request
        exchange_data = {
            "exchange_id": exchange_id,
            "user_id": request.user_id,
            "order_id": request.order_id,
            "product_sku": request.product_sku,
            "current_size": request.current_size,
            "requested_size": request.requested_size,
            "reason": request.reason or "Size exchange",
            "status": "initiated",
            "delivery_date": delivery_date,
            "timestamp": datetime.now().isoformat(),
            "order_verified": order_verified
        }
        
        redis_utils.store_exchange_request(exchange_id, exchange_data)
        
        return ExchangeResponse(
            success=True,
            exchange_id=exchange_id,
            status="initiated",
            message=(
                f"Exchange initiated. New size: {request.requested_size}. Expected delivery: {delivery_date}"
                if order_verified else
                f"Exchange received. We will verify order {request.order_id} and confirm delivery for size {request.requested_size}."
            ),
            new_product_sku=request.product_sku,  # Same SKU, different size
            delivery_date=delivery_date,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-purchase/complaint", response_model=ComplaintResponse)
async def raise_complaint(request: ComplaintRequest):
    """
    Raise a complaint or issue
    
    Steps:
    1. Validate issue type
    2. Generate complaint ID and ticket number
    3. Store complaint
    4. Notify support team
    """
    try:
        # Validate issue type
        if request.issue_type not in ISSUE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid issue type. Valid types: {ISSUE_TYPES}"
            )
        
        # Generate IDs
        complaint_id = f"CMP_{uuid.uuid4().hex[:12].upper()}"
        ticket_number = f"TKT{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        
        # Store complaint
        complaint_data = {
            "complaint_id": complaint_id,
            "ticket_number": ticket_number,
            "user_id": request.user_id,
            "order_id": request.order_id or "",
            "issue_type": request.issue_type,
            "description": request.description,
            "priority": request.priority,
            "status": "open",
            "timestamp": datetime.now().isoformat(),
            "assigned_to": "support_team"
        }
        
        redis_utils.store_complaint(complaint_id, complaint_data)
        
        return ComplaintResponse(
            success=True,
            complaint_id=complaint_id,
            status="open",
            ticket_number=ticket_number,
            message=f"Complaint registered. Ticket: {ticket_number}. Our support team will contact you within 24 hours.",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/post-purchase/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """Capture post-purchase feedback for service quality tracking"""
    try:
        feedback_id = f"FDB_{uuid.uuid4().hex[:12].upper()}"

        feedback_data = {
            "feedback_id": feedback_id,
            "user_id": request.user_id,
            "order_id": request.order_id or "",
            "product_sku": request.product_sku,
            "size_purchased": request.size_purchased or "",
            "fit_rating": request.fit_rating or "",
            "length_feedback": request.length_feedback or "",
            "comments": request.comments or "",
            "status": "received",
            "timestamp": datetime.now().isoformat()
        }

        redis_utils.store_feedback(feedback_id, feedback_data)

        return FeedbackResponse(
            success=True,
            feedback_id=feedback_id,
            status="received",
            message="Feedback recorded. Thanks for helping us improve!",
            timestamp=feedback_data["timestamp"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/post-purchase/returns/{user_id}")
async def get_user_returns(user_id: str, limit: int = 10):
    """
    Get user's return history
    Shows user's orders from orders.csv and their returns
    """
    try:
        # Get user's orders from orders.csv
        user_orders = redis_utils.get_user_orders(user_id)
        
        # Get returns from Redis
        returns = redis_utils.get_user_returns(user_id, limit)
        
        return {
            "user_id": user_id,
            "total_orders": len(user_orders),
            "orders": user_orders,
            "total_returns": len(returns),
            "returns": returns
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/post-purchase/issue-types")
async def get_issue_types():
    """Get list of issue types for complaints"""
    return {
        "issue_types": ISSUE_TYPES
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
