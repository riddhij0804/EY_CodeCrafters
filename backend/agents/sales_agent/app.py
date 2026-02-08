"""
Sales Agent FastAPI Application with LangGraph + Vertex AI

A production-ready sales agent that uses:
- Vertex AI (Gemini) for intelligent intent detection
- LangGraph for workflow orchestration
- Microservice architecture for business logic

"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / '.env')

# Import LangGraph Sales Agent (absolute import for direct uvicorn execution)
from sales_graph import process_message as process_with_langgraph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sales Agent API with LangGraph + Vertex AI",
    description="Intelligent sales agent powered by Vertex AI intent detection and LangGraph workflow",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class MessageRequest(BaseModel):
    """Request model for user messages."""
    message: str = Field(..., min_length=1, description="User message to the sales agent")
    session_token: Optional[str] = Field(None, description="Session token for conversation continuity")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Show me running shoes under 3000",
                "session_token": "abc123-def456",
                "metadata": {"user_id": "user_001", "source": "web"}
            }
        }


class AgentResponse(BaseModel):
    """Response model with intent information and cards."""
    reply: str = Field(..., description="Agent's response message")
    session_token: str = Field(..., description="Session token for tracking conversation")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: dict = Field(default_factory=dict, description="Additional response metadata")
    intent_info: Optional[dict] = Field(None, description="Intent detection information")
    cards: List[dict] = Field(default_factory=list, description="Product cards or visual elements")


class PostPaymentRequest(BaseModel):
    """Request model for post-payment processing after successful Razorpay payment."""
    order_id: str = Field(..., description="Order ID that was successfully paid")
    customer_id: str = Field(..., description="Customer ID who made the payment")
    session_token: str = Field(..., description="Session token for conversation continuity")
    amount_paid: float = Field(..., description="Amount that was successfully paid")
    payment_id: str = Field(..., description="Razorpay payment ID")
    transaction_id: Optional[str] = Field(None, description="Transaction ID from payment agent")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ORD000961",
                "customer_id": "user_001",
                "session_token": "abc123-def456",
                "amount_paid": 2999.00,
                "payment_id": "pay_1234567890",
                "transaction_id": "txn_1234567890"
            }
        }


# ============================================================================
# MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and responses."""
    logger.info(f"📨 {request.method} {request.url.path}")
    
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            logger.debug(f"Request body: {body.decode('utf-8')[:500]}")
            
            # Store body for route handler
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        except Exception as e:
            logger.error(f"Error reading request body: {e}")
    
    response = await call_next(request)
    logger.info(f"✅ Response: {response.status_code}")
    
    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.error(f"❌ Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Invalid request payload"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"❌ Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - service info."""
    return {
        "status": "running",
        "service": "Sales Agent with LangGraph + Vertex AI",
        "version": "2.0.0",
        "features": ["Vertex AI Intent Detection", "LangGraph Workflow", "Microservice Integration"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "Sales Agent with LangGraph + Vertex AI",
        "timestamp": datetime.utcnow().isoformat()
    }


class CheckoutRequest(BaseModel):
    """Request model for checkout."""
    customer_id: str = Field(..., description="Customer ID")
    items: List[Dict[str, Any]] = Field(..., description="List of items to purchase")
    payment_method: Dict[str, Any] = Field(..., description="Payment method details")
    shipping_address: Dict[str, Any] = Field(..., description="Shipping address")
    session_token: Optional[str] = Field(None, description="Session token")


@app.post("/api/checkout")
async def handle_checkout(request: CheckoutRequest):
    """
    Complete checkout flow: inventory -> payment -> fulfillment.
    
    This endpoint orchestrates the full purchase flow across all microservices:
    1. Verify inventory availability
    2. Create inventory holds
    3. Process payment
    4. Start fulfillment
    5. Persist order record
    
    Args:
        request: CheckoutRequest with customer, items, payment, and shipping info
        
    Returns:
        Order completion status with order_id and fulfillment details
    """
    logger.info(f"🛒 Checkout initiated for customer: {request.customer_id}")
    
    try:
        # Import the agent client
        from agent_client import SalesAgentClient
        
        # Create agent instance
        agent = SalesAgentClient()
        
        # Execute complete purchase flow
        result = await agent.complete_purchase_flow(
            customer_id=request.customer_id,
            items=request.items,
            payment_method=request.payment_method,
            shipping_address=request.shipping_address
        )
        
        logger.info(f"✅ Checkout completed: {result['status']} - Order: {result.get('order_id')}")
        
        # Return formatted response
        return {
            "status": result['status'],
            "order_id": result.get('order_id'),
            "steps": result.get('steps', {}),
            "message": "Order placed successfully" if result['status'] == 'completed' else f"Order {result['status']}"
        }
        
    except Exception as e:
        logger.error(f"❌ Checkout failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "message": "Failed to process checkout"
            }
        )


@app.post("/api/post-payment")
async def handle_post_payment(request: PostPaymentRequest):
    """
    Handle post-payment processing after successful Razorpay payment verification.

    This endpoint is called by the frontend after successful payment verification
    to trigger the full post-payment agent workflow:
    1. Start fulfillment processing
    2. Notify post-purchase agent
    3. Trigger stylist analysis
    4. Update inventory

    Args:
        request: PostPaymentRequest with verified payment details

    Returns:
        Processing status and agent responses
    """
    logger.info(f"💰 Post-payment processing for order: {request.order_id}")

    try:
        # Create a mock state for the fulfillment worker
        from sales_graph import SalesAgentState

        state = SalesAgentState(
            message=f"Payment completed for order {request.order_id}",
            session_token=request.session_token,
            metadata={
                "order_id": request.order_id,
                "customer_id": request.customer_id,
                "source": "post_payment",
                "action": "start_processing",
                "trigger_agents": ["fulfillment", "post_purchase", "stylist", "inventory"],
                "amount_paid": request.amount_paid,
                "payment_id": request.payment_id,
                "transaction_id": request.transaction_id
            },
            intent="support",  # Routes to fulfillment_worker
            confidence=1.0,
            entities={
                "order_id": request.order_id,
                "customer_id": request.customer_id,
                "source": "post_payment",
                "action": "start_processing",
                "trigger_agents": ["fulfillment", "post_purchase", "stylist", "inventory"]
            },
            intent_method="post_payment_trigger",
            response="",
            cards=[],
            worker_service="",
            worker_url="",
            error=""
        )

        # Import and call the fulfillment worker directly
        from sales_graph import call_fulfillment_worker
        result_state = await call_fulfillment_worker(state)

        logger.info(f"✅ Post-payment processing completed for order {request.order_id}")

        return {
            "status": "success",
            "order_id": request.order_id,
            "message": result_state.response,
            "processing_started": True,
            "agents_triggered": ["fulfillment", "post_purchase", "stylist", "inventory"]
        }

    except Exception as e:
        logger.error(f"❌ Post-payment processing failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "message": "Failed to process post-payment workflow"
            }
        )


@app.post("/api/message", response_model=AgentResponse)
async def handle_message(request: MessageRequest):
    """
    Handle incoming user messages using LangGraph + Vertex AI workflow.
    
    Flow:
        1. User message received
        2. Fetch conversation history from session
        3. Run LangGraph workflow:
           - Intent Detection (Vertex AI)
           - Router (based on intent)
           - Worker Microservice Call
        4. Return structured response to frontend
    
    Args:
        request: MessageRequest with user message and metadata
        
    Returns:
        AgentResponse with reply, intent info, and product cards
    """
    logger.info(f"📨 Message: '{request.message[:100]}...'" )

    # Generate or reuse session token
    session_token = request.session_token or str(uuid.uuid4())
    
    # Fetch conversation history and session data for context
    conversation_history = []
    enhanced_metadata = request.metadata.copy() if request.metadata else {}
    
    if request.session_token:
        try:
            sess_resp = requests.get(
                "http://localhost:8000/session/restore",
                headers={"X-Session-Token": request.session_token},
                timeout=8
            )
            if sess_resp.status_code == 200:
                sess = sess_resp.json().get("session", {})
                conversation_history = sess.get("data", {}).get("chat_context", [])
                
                # Enhance metadata with session data
                enhanced_metadata["phone"] = sess.get("phone")
                enhanced_metadata["user_id"] = sess.get("user_id")
                enhanced_metadata["session_id"] = sess.get("session_id")
                enhanced_metadata["customer_id"] = sess.get("customer_id")
                
                logger.info(f"📚 Retrieved {len(conversation_history)} conversation turns")
                logger.info(f"📞 Session phone: {sess.get('phone')}")
        except Exception as e:
            logger.warning(f"⚠️  Could not fetch conversation history: {e}")
    
    try:
        # Execute LangGraph workflow
        logger.info("🔄 Running LangGraph workflow...")
        result = await process_with_langgraph(
            message=request.message,
            session_token=session_token,
            metadata=enhanced_metadata,
            conversation_history=conversation_history
        )
        
        # Format response for frontend
        response = AgentResponse(
            reply=result["response"],
            session_token=session_token,
            timestamp=result["timestamp"],
            metadata={
                "processed": True,
                "worker": result["worker"],
                "original_metadata": request.metadata
            },
            intent_info={
                "intent": result["intent"],
                "confidence": result["confidence"],
                "entities": result["entities"],
                "method": result["method"]
            },
            cards=result.get("cards", [])
        )
        
        logger.info(
            f"✅ Response generated via {result['worker']} "
            f"(intent: {result['intent']}, confidence: {result['confidence']:.2f})"
        )
        
        # Save to session if available
        if request.session_token:
            try:
                base_headers = {"X-Session-Token": request.session_token}

                requests.post(
                    "http://localhost:8000/session/update",
                    headers=base_headers,
                    json={
                        "action": "chat_message",
                        "payload": {
                            "sender": "user",
                            "message": request.message,
                            "metadata": {"intent": result["intent"]}
                        }
                    },
                    timeout=6
                )

                requests.post(
                    "http://localhost:8000/session/update",
                    headers=base_headers,
                    json={
                        "action": "chat_message",
                        "payload": {
                            "sender": "agent",
                            "message": result["response"],
                            "metadata": {
                                "intent": result["intent"],
                                "confidence": result["confidence"],
                                "method": result["method"]
                            }
                        }
                    },
                    timeout=6
                )
            except Exception as e:
                logger.warning(f"⚠️  Could not save to session: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ LangGraph workflow failed: {e}", exc_info=True)
        
        # Fallback response
        return AgentResponse(
            reply="I'm having trouble processing your request right now. Please try again.",
            session_token=session_token,
            timestamp=datetime.utcnow().isoformat(),
            metadata={"error": str(e), "processed": False},
            intent_info={
                "intent": "error",
                "confidence": 0.0,
                "entities": {},
                "method": "error_fallback"
            },
            cards=[]
        )


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="info"
    )
