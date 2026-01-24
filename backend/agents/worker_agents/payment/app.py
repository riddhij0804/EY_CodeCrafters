# Payment Agent - FastAPI Server
# Endpoints: POST /payment/process, GET /payment/transaction/{txn_id}, GET /payment/user-transactions/{user_id}

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Optional
import uvicorn
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import json
import logging
import os
import requests
print(">>> Razorpay router loaded")
try:
    import razorpay
except ImportError:  # pragma: no cover - dependency managed via requirements
    razorpay = None

import redis_utils
import payment_repository

app = FastAPI(
    title="Payment Agent",
    description="Payment processing and transaction management system",
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


logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
LOYALTY_SERVICE_URL = os.getenv("LOYALTY_SERVICE_URL", "http://localhost:8002")

razorpay_client = None
razorpay_router = APIRouter(prefix="/payment/razorpay", tags=["Razorpay"])


def _ensure_razorpay_client():
    """Return an initialised Razorpay client or raise an HTTP error."""
    global razorpay_client

    if razorpay is None:
        raise HTTPException(
            status_code=500,
            detail="Razorpay SDK not installed. Run pip install razorpay.",
        )

    if not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):
        raise HTTPException(
            status_code=503,
            detail="Razorpay credentials not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.",
        )

    if razorpay_client is None:
        logger.info("Initialising Razorpay test client")
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

    return razorpay_client


def _quantize(value: Decimal) -> str:
    """Format Decimal values with two decimal places for CSV storage."""
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _store_transaction_safely(transaction_id: str, data: Dict[str, str], user_key: str, amount: Decimal) -> None:
    """Persist Razorpay transactions to Redis, ignoring missing client errors."""
    try:
        redis_utils.store_transaction(transaction_id, data)
        redis_utils.store_payment_attempt(user_key, {
            "transaction_id": transaction_id,
            "amount": float(amount),
            "status": data.get("status", "success"),
        })
    except RuntimeError:
        logger.debug("Redis not configured; skipped caching Razorpay payment")


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class PaymentRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., description="Payment method: upi, card, wallet, netbanking, cod")
    order_id: Optional[str] = Field(None, description="Associated order ID")
    metadata: dict = Field(default_factory=dict, description="Additional payment metadata")


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str
    amount: float
    payment_method: str
    gateway_txn_id: Optional[str]
    cashback: float
    message: str
    timestamp: str
    order_id: Optional[str]


class TransactionResponse(BaseModel):
    transaction_id: str
    user_id: str
    amount: str
    payment_method: str
    status: str
    gateway_txn_id: Optional[str]
    timestamp: str
    order_id: Optional[str]


class RefundRequest(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID to refund")
    amount: Optional[float] = Field(None, description="Refund amount (partial or full)")
    reason: str = Field(..., description="Reason for refund")


class RefundResponse(BaseModel):
    success: bool
    refund_id: str
    transaction_id: str
    refund_amount: float
    message: str
    timestamp: str


class AuthorizationRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    amount: float = Field(..., gt=0, description="Amount to authorize")
    payment_method: str = Field(..., description="Payment method")
    order_id: str = Field(..., description="Order ID")


class AuthorizationResponse(BaseModel):
    success: bool
    authorization_id: str
    amount: float
    status: str  # authorized, declined
    message: str
    timestamp: str


class CaptureRequest(BaseModel):
    authorization_id: str = Field(..., description="Authorization ID to capture")
    amount: Optional[float] = Field(None, description="Amount to capture (partial or full)")


class CaptureResponse(BaseModel):
    success: bool
    transaction_id: str
    authorization_id: str
    captured_amount: float
    message: str
    timestamp: str


class POSRequest(BaseModel):
    store_id: str = Field(..., description="Store ID")
    terminal_id: str = Field(..., description="POS terminal ID")
    barcode: str = Field(..., description="Product barcode scanned")
    payment_method: str = Field(..., description="Payment method: card, upi, cash")
    amount: float = Field(..., gt=0, description="Transaction amount")


class POSResponse(BaseModel):
    success: bool
    transaction_id: str
    store_id: str
    terminal_id: str
    barcode: str
    amount: float
    payment_method: str
    message: str
    timestamp: str


class RazorpayCreateOrderRequest(BaseModel):
    amount_rupees: float = Field(..., gt=0, description="Amount to collect via Razorpay test order")
    currency: str = Field("INR", description="Three letter currency code")
    receipt: Optional[str] = Field(None, description="Optional receipt identifier shown in Razorpay dashboard")
    notes: Dict[str, str] = Field(default_factory=dict, description="Additional metadata forwarded to Razorpay")


class RazorpayVerifyRequest(BaseModel):
    razorpay_payment_id: str = Field(..., description="Payment ID returned by Razorpay Checkout")
    razorpay_order_id: str = Field(..., description="Order ID returned during create-order")
    razorpay_signature: Optional[str] = Field(None, description="Signature for server-side verification")
    amount_rupees: Optional[float] = Field(None, gt=0, description="Captured amount in rupees")
    method: Optional[str] = Field(None, description="Payment method recorded for this transaction")
    discount_applied: Optional[float] = Field(0.0, ge=0, description="Applied discount value")
    gst: Optional[float] = Field(None, ge=0, description="GST amount for record keeping")
    idempotency_key: Optional[str] = Field(None, description="Client supplied idempotency key")
    user_id: Optional[str] = Field(None, description="User reference for auditing")


# ==========================================
# ROUTES
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Payment Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@razorpay_router.post("/create-order")
async def create_razorpay_order(payload: RazorpayCreateOrderRequest):
    """Create a Razorpay order in test mode (no real charge)."""
    client = _ensure_razorpay_client()

    amount_rupees = Decimal(str(payload.amount_rupees))
    if amount_rupees <= 0:
        raise HTTPException(status_code=400, detail="amount_rupees must be greater than zero")

    amount_rupees = amount_rupees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amount_paise = int((amount_rupees * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    currency = (payload.currency or "INR").upper()

    order_payload = {
        "amount": amount_paise,
        "currency": currency,
        "payment_capture": 1,
    }
    if payload.receipt:
        order_payload["receipt"] = payload.receipt
    if payload.notes:
        order_payload["notes"] = payload.notes

    order = client.order.create(order_payload)

    return {
        "order": order,
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "amount_rupees": _quantize(amount_rupees),
    }


@razorpay_router.post("/verify-payment")
async def verify_razorpay_payment(payload: RazorpayVerifyRequest):
    """Record a Razorpay test payment as successful and persist it."""
    if not payload.razorpay_payment_id or not payload.razorpay_order_id:
        raise HTTPException(status_code=400, detail="razorpay_payment_id and razorpay_order_id are required")

    amount_rupees = Decimal(str(payload.amount_rupees)) if payload.amount_rupees is not None else Decimal("0")
    if amount_rupees < 0:
        raise HTTPException(status_code=400, detail="amount_rupees cannot be negative")

    amount_rupees = amount_rupees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount_value = Decimal(str(payload.discount_applied)) if payload.discount_applied is not None else Decimal("0")
    discount_value = discount_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if payload.gst is not None:
        gst_value = Decimal(str(payload.gst)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif amount_rupees:
        gst_value = (amount_rupees * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        gst_value = Decimal("0.00")

    method = (payload.method or "upi").lower()
    idempotency_key = payload.idempotency_key or f"idemp_{payload.razorpay_payment_id}"
    timestamp = datetime.now().isoformat()

    payment_repository.upsert_payment_record({
        "payment_id": payload.razorpay_payment_id,
        "order_id": payload.razorpay_order_id,
        "status": "success",
        "amount_rupees": _quantize(amount_rupees),
        "discount_applied": _quantize(discount_value),
        "gst": _quantize(gst_value),
        "method": method,
        "gateway_ref": payload.razorpay_payment_id,
        "idempotency_key": idempotency_key,
        "created_at": timestamp,
    })

    metadata = {
        "idempotency_key": idempotency_key,
        "razorpay_signature": payload.razorpay_signature,
    }

    transaction_payload = {
        "transaction_id": payload.razorpay_payment_id,
        "user_id": payload.user_id or "",
        "amount": _quantize(amount_rupees),
        "payment_method": method,
        "status": "success",
        "gateway_txn_id": payload.razorpay_payment_id,
        "cashback": "0",
        "timestamp": timestamp,
        "order_id": payload.razorpay_order_id,
        "metadata": json.dumps(metadata),
    }

    user_key = payload.user_id or payload.razorpay_payment_id
    _store_transaction_safely(payload.razorpay_payment_id, transaction_payload, user_key, amount_rupees)

    return {"status": "ok", "payment_id": payload.razorpay_payment_id}


app.include_router(razorpay_router)


@app.post("/payment/process", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest):
    """
    Process a payment transaction
    Steps:
    1. Validate payment method
    2. Simulate payment gateway call
    3. Calculate cashback
    4. Store transaction details
    5. Return response
    """
    try:
        # Step 1: Validate payment method
        if not redis_utils.validate_payment_method(request.payment_method):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid payment method: {request.payment_method}. Supported: upi, card, wallet, netbanking, cod"
            )
        
        # Step 2: Generate transaction ID
        transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        
        # Step 3: Simulate payment gateway
        gateway_response = redis_utils.simulate_payment_gateway(
            request.payment_method,
            request.amount
        )
        
        if not gateway_response["success"]:
            raise HTTPException(status_code=400, detail=gateway_response["message"])
        
        # Step 4: Calculate cashback
        cashback = redis_utils.calculate_cashback(request.amount, request.payment_method)
        
        # Step 5: Store transaction
        transaction_data = {
            "transaction_id": transaction_id,
            "user_id": request.user_id,
            "amount": str(request.amount),
            "payment_method": request.payment_method,
            "status": "success",
            "gateway_txn_id": gateway_response["gateway_txn_id"],
            "cashback": str(cashback),
            "timestamp": datetime.now().isoformat(),
            "order_id": request.order_id or "",
            "metadata": str(request.metadata)
        }
        
        redis_utils.store_transaction(transaction_id, transaction_data)
        
        # Step 6: Log payment attempt
        redis_utils.store_payment_attempt(request.user_id, {
            "transaction_id": transaction_id,
            "amount": request.amount,
            "status": "success"
        })
        # Step 7: Award loyalty points after successful payment
        loyalty_result = None
        try:
            # Call loyalty service to earn points (1 point per ₹10 spent)
            loyalty_response = requests.post(
                f"{LOYALTY_SERVICE_URL}/loyalty/earn-from-purchase",
                params={"user_id": request.user_id, "amount_spent": request.amount},
                timeout=5
            )
            if loyalty_response.ok:
                loyalty_result = loyalty_response.json()
                logger.info(f"✅ Loyalty points awarded: {loyalty_result.get('total_points_earned', 0)} points to user {request.user_id}")
            else:
                logger.warning(f"⚠️  Loyalty service returned {loyalty_response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to award loyalty points: {e}")
        
        # Build response message
        response_message = f"{gateway_response['message']}. Cashback: ₹{cashback}"
        if loyalty_result and loyalty_result.get('success'):
            points_earned = loyalty_result.get('total_points_earned', 0)
            response_message += f" | Earned {points_earned} loyalty points!"
            if loyalty_result.get('tier_upgraded'):
                new_tier = loyalty_result.get('current_tier')
                response_message += f" 🏆 Upgraded to {new_tier}!"
        
        return PaymentResponse(
            success=True,
            transaction_id=transaction_id,
            amount=request.amount,
            payment_method=request.payment_method,
            gateway_txn_id=gateway_response["gateway_txn_id"],
            cashback=cashback,
            message=response_message
            message=f"{gateway_response['message']}. Cashback: ₹{cashback}",
            timestamp=datetime.now().isoformat(),
            order_id=request.order_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/payment/transaction/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str):
    """Retrieve transaction details by transaction ID"""
    try:
        transaction = redis_utils.get_transaction(transaction_id)
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return TransactionResponse(
            transaction_id=transaction["transaction_id"],
            user_id=transaction["user_id"],
            amount=transaction["amount"],
            payment_method=transaction["payment_method"],
            status=transaction["status"],
            gateway_txn_id=transaction.get("gateway_txn_id"),
            timestamp=transaction["timestamp"],
            order_id=transaction.get("order_id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/payment/user-transactions/{user_id}")
async def get_user_transactions(user_id: str, limit: int = 10):
    """Get recent transactions for a user"""
    try:
        transactions = redis_utils.get_user_transactions(user_id, limit)
        
        return {
            "user_id": user_id,
            "transaction_count": len(transactions),
            "transactions": transactions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/payment/refund", response_model=RefundResponse)
async def process_refund(request: RefundRequest):
    """
    Process a refund for a transaction
    """
    try:
        # Retrieve original transaction
        transaction = redis_utils.get_transaction(request.transaction_id)
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Get original amount
        original_amount = float(transaction["amount"])
        
        # Determine refund amount
        refund_amount = request.amount if request.amount else original_amount
        
        if refund_amount > original_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Refund amount cannot exceed original amount of ₹{original_amount}"
            )
        
        # Generate refund ID
        refund_id = f"REFUND_{uuid.uuid4().hex[:12].upper()}"
        
        # Store refund transaction
        refund_data = {
            "refund_id": refund_id,
            "transaction_id": request.transaction_id,
            "user_id": transaction["user_id"],
            "refund_amount": str(refund_amount),
            "original_amount": str(original_amount),
            "reason": request.reason,
            "status": "processed",
            "timestamp": datetime.now().isoformat()
        }
        
        redis_utils.store_transaction(refund_id, refund_data)
        
        return RefundResponse(
            success=True,
            refund_id=refund_id,
            transaction_id=request.transaction_id,
            refund_amount=refund_amount,
            message=f"Refund of ₹{refund_amount} processed successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/payment/methods")
async def get_payment_methods():
    """Get list of supported payment methods"""
    return {
        "supported_methods": [
            {
                "id": "upi",
                "name": "UPI",
                "cashback": "1%",
                "processing_time": "Instant"
            },
            {
                "id": "card",
                "name": "Credit/Debit Card",
                "cashback": "2%",
                "processing_time": "Instant"
            },
            {
                "id": "wallet",
                "name": "Digital Wallet",
                "cashback": "1.5%",
                "processing_time": "Instant"
            },
            {
                "id": "netbanking",
                "name": "Net Banking",
                "cashback": "0.5%",
                "processing_time": "2-3 minutes"
            },
            {
                "id": "cod",
                "name": "Cash on Delivery",
                "cashback": "0%",
                "processing_time": "On delivery"
            }
        ]
    }


@app.post("/payment/authorize", response_model=AuthorizationResponse)
async def authorize_payment(request: AuthorizationRequest):
    """
    Payment Gateway Stub: Authorize payment (pre-authorization)
    This simulates authorization without capturing funds
    Can be declined based on random simulation
    """
    try:
        import random
        
        # Validate payment method
        if not redis_utils.validate_payment_method(request.payment_method):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid payment method: {request.payment_method}"
            )
        
        # Generate authorization ID
        auth_id = f"AUTH_{uuid.uuid4().hex[:12].upper()}"
        
        # Simulate authorization with 10% decline rate
        is_declined = random.random() < 0.1
        
        if is_declined:
            # Store declined authorization
            auth_data = {
                "authorization_id": auth_id,
                "user_id": request.user_id,
                "amount": str(request.amount),
                "payment_method": request.payment_method,
                "order_id": request.order_id,
                "status": "declined",
                "reason": "Insufficient funds or card declined",
                "timestamp": datetime.now().isoformat()
            }
            redis_utils.store_transaction(auth_id, auth_data)
            
            return AuthorizationResponse(
                success=False,
                authorization_id=auth_id,
                amount=request.amount,
                status="declined",
                message="Payment authorization declined. Please try a different payment method.",
                timestamp=datetime.now().isoformat()
            )
        
        # Store successful authorization
        auth_data = {
            "authorization_id": auth_id,
            "user_id": request.user_id,
            "amount": str(request.amount),
            "payment_method": request.payment_method,
            "order_id": request.order_id,
            "status": "authorized",
            "timestamp": datetime.now().isoformat(),
            "captured": "false"
        }
        redis_utils.store_transaction(auth_id, auth_data)
        
        return AuthorizationResponse(
            success=True,
            authorization_id=auth_id,
            amount=request.amount,
            status="authorized",
            message=f"Payment of ₹{request.amount} authorized successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/payment/capture", response_model=CaptureResponse)
async def capture_payment(request: CaptureRequest):
    """
    Payment Gateway Stub: Capture authorized payment
    This finalizes the transaction and transfers funds
    """
    try:
        # Retrieve authorization
        auth_data = redis_utils.get_transaction(request.authorization_id)
        
        if not auth_data:
            raise HTTPException(status_code=404, detail="Authorization not found")
        
        if auth_data.get("status") != "authorized":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot capture. Authorization status: {auth_data.get('status')}"
            )
        
        if auth_data.get("captured") == "true":
            raise HTTPException(status_code=400, detail="Authorization already captured")
        
        # Determine capture amount
        authorized_amount = float(auth_data["amount"])
        capture_amount = request.amount if request.amount else authorized_amount
        
        if capture_amount > authorized_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Capture amount cannot exceed authorized amount of ₹{authorized_amount}"
            )
        
        # Generate transaction ID
        txn_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        
        # Calculate cashback
        cashback = redis_utils.calculate_cashback(capture_amount, auth_data["payment_method"])
        
        # Store captured transaction
        txn_data = {
            "transaction_id": txn_id,
            "authorization_id": request.authorization_id,
            "user_id": auth_data["user_id"],
            "amount": str(capture_amount),
            "payment_method": auth_data["payment_method"],
            "status": "captured",
            "cashback": str(cashback),
            "timestamp": datetime.now().isoformat(),
            "order_id": auth_data.get("order_id", "")
        }
        redis_utils.store_transaction(txn_id, txn_data)
        
        # Update authorization as captured
        auth_data["captured"] = "true"
        auth_data["capture_txn_id"] = txn_id
        redis_utils.store_transaction(request.authorization_id, auth_data)
        
        return CaptureResponse(
            success=True,
            transaction_id=txn_id,
            authorization_id=request.authorization_id,
            captured_amount=capture_amount,
            message=f"Payment of ₹{capture_amount} captured successfully. Cashback: ₹{cashback}",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/payment/pos", response_model=POSResponse)
async def process_pos_payment(request: POSRequest):
    """
    POS Integration: Simulated in-store terminal interactions
    Handles barcode scan and payment processing at physical stores
    """
    try:
        # Validate store and terminal
        if not request.store_id or not request.terminal_id:
            raise HTTPException(status_code=400, detail="Invalid store or terminal ID")
        
        # Validate barcode (simulate product lookup)
        if len(request.barcode) < 8:
            raise HTTPException(status_code=400, detail="Invalid barcode format")
        
        # Validate payment method for POS
        valid_pos_methods = ["card", "upi", "cash"]
        if request.payment_method not in valid_pos_methods:
            raise HTTPException(
                status_code=400,
                detail=f"Payment method not supported for POS. Use: {', '.join(valid_pos_methods)}"
            )
        
        # Generate POS transaction ID
        pos_txn_id = f"POS_{request.store_id}_{uuid.uuid4().hex[:8].upper()}"
        
        # Simulate payment processing
        import random
        is_success = random.random() > 0.05  # 95% success rate
        
        if not is_success:
            raise HTTPException(
                status_code=400,
                detail="POS transaction failed. Please retry or use alternative payment method."
            )
        
        # Store POS transaction
        pos_data = {
            "transaction_id": pos_txn_id,
            "type": "pos",
            "store_id": request.store_id,
            "terminal_id": request.terminal_id,
            "barcode": request.barcode,
            "amount": str(request.amount),
            "payment_method": request.payment_method,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
        redis_utils.store_transaction(pos_txn_id, pos_data)
        
        return POSResponse(
            success=True,
            transaction_id=pos_txn_id,
            store_id=request.store_id,
            terminal_id=request.terminal_id,
            barcode=request.barcode,
            amount=request.amount,
            payment_method=request.payment_method,
            message=f"POS payment of ₹{request.amount} processed successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
