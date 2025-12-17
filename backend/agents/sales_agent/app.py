import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
import re
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sales Agent API",
    description="API for handling sales agent conversations",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to the sales agent")
    session_token: Optional[str] = Field(None, description="Session token for conversation continuity")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I'm interested in your product",
                "session_token": "abc123-def456",
                "metadata": {"user_id": "user_001", "source": "web"}
            }
        }


class ResumeSessionRequest(BaseModel):
    session_token: str = Field(..., min_length=1, description="Session token to resume")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "session_token": "abc123-def456",
                "metadata": {"user_id": "user_001"}
            }
        }


class AgentResponse(BaseModel):
    reply: str = Field(..., description="Agent's response message")
    session_token: str = Field(..., description="Session token for tracking conversation")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: dict = Field(default_factory=dict, description="Additional response metadata")


# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log incoming request
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    
    # Get request body for logging (be careful with large payloads in production)
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            logger.info(f"Request body: {body.decode('utf-8')[:500]}")  # Limit log size
            
            # Important: Store body for route handler to access
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        except Exception as e:
            logger.error(f"Error reading request body: {e}")
    
    # Process request
    response = await call_next(request)
    
    # Log response status
    logger.info(f"Response status: {response.status_code}")
    
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
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
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Sales Agent API",
        "version": "1.0.0"
    }


@app.post("/api/message", response_model=AgentResponse)
async def handle_message(request: MessageRequest):
    """
    Handle incoming user messages and generate agent responses
    
    This is a placeholder endpoint that returns dummy responses.
    In production, this would integrate with LLM logic.
    """
    logger.info(f"Processing message: '{request.message[:200]}...'" )

    # Generate or reuse session token
    session_token = request.session_token or str(uuid.uuid4())

    # Lightweight intent detection (rule-based)
    def detect_intent(text: str) -> Dict[str, Any]:
        t = text.lower()
        intent = {"type": "fallback", "intent": {}}

        # Gift detection
        if re.search(r"\b(gift|present|for my|for her|for him|wife|husband|mom|mother|dad|father|birthday)\b", t):
            intent["type"] = "recommendation"
            # Prefer explicit occasion 'birthday' when mentioned
            if re.search(r"\bbirthday\b", t):
                intent["intent"] = {"occasion": "birthday"}
            else:
                intent["intent"] = {"occasion": "gift"}

            # recipient relation and gender inference
            if re.search(r"\b(mom|mother|mum|mummy)\b", t):
                intent["intent"]["recipient_relation"] = "mother"
                intent["intent"]["gender"] = "female"
            elif re.search(r"\b(dad|father|papa)\b", t):
                intent["intent"]["recipient_relation"] = "father"
                intent["intent"]["gender"] = "male"
            elif re.search(r"\b(sister)\b", t):
                intent["intent"]["recipient_relation"] = "sister"
                intent["intent"]["gender"] = "female"
            elif re.search(r"\b(brother)\b", t):
                intent["intent"]["recipient_relation"] = "brother"
                intent["intent"]["gender"] = "male"
            elif re.search(r"\b(wife|spouse|wifey)\b", t):
                intent["intent"]["recipient_relation"] = "wife"
                intent["intent"]["gender"] = "female"
            elif re.search(r"\b(husband|spouse|hubby)\b", t):
                intent["intent"]["recipient_relation"] = "husband"
                intent["intent"]["gender"] = "male"
            return intent

        # Recommendation keywords
        if re.search(r"\b(recommend|suggest|show me|any options|looking for|what are|something like)\b", t):
            intent["type"] = "recommendation"
            # try to extract simple category and budget
            m_cat = re.search(r"(footwear|shoes|apparel|clothes|jacket|shirt|pants|accessories|watch|bag|sneaker)s?", t)
            if m_cat:
                intent["intent"]["category"] = m_cat.group(1).capitalize()
            m_budget = re.search(r"under\s*(?:rs|₹|inr)?\s*(\d{3,6})", t)
            if m_budget:
                intent["intent"]["budget_max"] = int(m_budget.group(1))
            return intent

        # Inventory / availability check
        if re.search(r"\b(in stock|available|stock|availability|is there)\b", t):
            intent["type"] = "inventory"
            m_sku = re.search(r"(sku\s*[:#]?\s*\w+|sku\w+|[A-Z]{2,}-?\d{3,6})", request.message, re.I)
            if m_sku:
                intent["intent"]["sku"] = m_sku.group(0)
            return intent

        # Checkout / payment
        if re.search(r"\b(buy|checkout|order|pay|purchase|place order)\b", t):
            intent["type"] = "payment"
            return intent

        return intent

    detected = detect_intent(request.message)
    logger.info(f"Detected intent: {detected}")

    # Helper: extract customer id or phone from a follow-up message
    def extract_customer_id(text: str) -> Optional[str]:
        m = re.search(r"(?:customer\s*id|customerid|cust\s*id|id)\s*[:#]?\s*(\d{2,12})", text, re.I)
        if m:
            return m.group(1)
        # bare numeric fallback (only if message is short)
        m2 = re.search(r"\b(\d{2,12})\b", text)
        if m2 and len(text.strip()) < 40:
            return m2.group(1)
        return None

    customer_id_in_message = extract_customer_id(request.message)
    # If user provided a customer id as a follow-up, try to resume pending recommendation
    if customer_id_in_message and detected.get("type") != "recommendation":
        logger.info(f"Found customer id in message: {customer_id_in_message}. Attempting to resume pending flow.")
        # Attempt to fetch session chat context to find last user intent that caused the missing field
        if request.session_token:
            try:
                sess_resp = requests.get("http://localhost:8000/session/restore", headers={"X-Session-Token": request.session_token}, timeout=3)
                if sess_resp.status_code == 200:
                    sess = sess_resp.json().get("session", {})
                    chat_ctx = sess.get("data", {}).get("chat_context", [])
                    # find last agent message that asked for missing fields
                    last_agent_idx = None
                    for i in range(len(chat_ctx)-1, -1, -1):
                        if chat_ctx[i].get("sender") == "agent":
                            last_agent_idx = i
                            break

                    # find the user message immediately before that agent prompt
                    prior_user_msg = None
                    if last_agent_idx is not None and last_agent_idx > 0:
                        for j in range(last_agent_idx-1, -1, -1):
                            if chat_ctx[j].get("sender") == "user":
                                prior_user_msg = chat_ctx[j].get("message")
                                break

                    if prior_user_msg:
                        logger.info(f"Re-detecting intent from prior user message: {prior_user_msg}")
                        prior_intent = detect_intent(prior_user_msg)
                        logger.info(f"Prior intent detected as: {prior_intent}")
                        # If prior intent was recommendation, set up a recommendation call using provided id
                        if prior_intent.get("type") == "recommendation":
                            # override metadata with supplied customer id and call recommendation worker
                            request.metadata["user_id"] = customer_id_in_message
                            # Persist user_id into session store so it is remembered for this session
                            try:
                                update_payload = {"action": "set_user", "payload": {"user_id": customer_id_in_message}}
                                # session update endpoint expects JSON body with action/payload and X-Session-Token header
                                uresp = requests.post("http://localhost:8000/session/update", headers={"X-Session-Token": request.session_token, "Content-Type": "application/json"}, json={"action": "set_user", "payload": {"user_id": customer_id_in_message}}, timeout=3)
                                logger.info(f"Session update set_user response: {uresp.status_code}")
                            except Exception as e:
                                logger.warning(f"Failed to persist user_id to session: {e}")
                            detected = prior_intent
                            logger.info("Resubmitting recommendation request with provided customer id")
                        else:
                            # acknowledge customer id but no pending recommendation
                            reply_text = f"Thanks — noted your customer id {customer_id_in_message}. How can I help you next?"
                            metadata.update({"noted_customer_id": customer_id_in_message})
                            response = AgentResponse(
                                reply=reply_text or "",
                                session_token=session_token,
                                timestamp=datetime.utcnow().isoformat(),
                                metadata=metadata
                            )
                            logger.info(f"Responding for session: {session_token}")
                            return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not restore session to resume flow: {e}")
        else:
            # If no session token but user provided customer id, create a lightweight session
            logger.info("No session token provided; creating a temporary session to persist customer id")
            try:
                start_resp = requests.post("http://localhost:8000/session/start", json={"phone": f"cid-{customer_id_in_message}", "channel": "web"}, timeout=3)
                if start_resp.status_code == 200:
                    start_data = start_resp.json()
                    new_token = start_data.get("session_token")
                    # Persist user id into this new session
                    try:
                        uresp = requests.post("http://localhost:8000/session/update", headers={"X-Session-Token": new_token, "Content-Type": "application/json"}, json={"action": "set_user", "payload": {"user_id": customer_id_in_message}}, timeout=3)
                        logger.info(f"Created session {new_token} and set user_id: {uresp.status_code}")
                        # set local session_token and request.session_token so later response returns token
                        session_token = new_token
                        request.session_token = new_token
                        # Also set metadata so recommendation flow uses this id
                        request.metadata["user_id"] = customer_id_in_message
                        detected = prior_intent if 'prior_intent' in locals() else detected
                        logger.info("Resubmitting recommendation request with newly created session and provided customer id")
                    except Exception as e:
                        logger.warning(f"Failed to persist user_id to newly created session: {e}")
                else:
                    logger.warning(f"Session start failed: {start_resp.status_code} {start_resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Failed to create session to persist customer id: {e}")

    # Route to worker agents
    reply_text = None
    metadata = {"agent_type": "sales", "processed": True, "original_metadata": request.metadata, "detected": detected}

    try:
        if detected["type"] == "recommendation":
            # Ensure required information is present before calling recommendation worker
            customer_id = request.metadata.get("user_id") or request.metadata.get("customer_id")
            required_fields = []

            if not customer_id:
                required_fields.append("user_id")

            # If this looks like a gifting request, require recipient info if not provided
            if detected.get("intent", {}).get("occasion") == "gift":
                if not detected.get("intent", {}).get("gender"):
                    required_fields.append("recipient_gender")

            if required_fields:
                # Ask the user for missing information instead of calling worker
                missing = ", ".join(required_fields)
                reply_text = f"I need a bit more info to help — please provide: {missing}."
                metadata.update({"missing_required_fields": required_fields})
            else:
                # Call recommendation service (customer_id present)
                # Build payload and prefer gifting mode when recipient info present
                payload = {
                    "customer_id": customer_id,
                    "intent": detected.get("intent", {}),
                    "current_cart_skus": request.metadata.get("cart_skus", []),
                    "limit": 5
                }
                # If this is a gifting request with recipient info, request gifting_genius mode
                if detected.get("intent", {}).get("recipient_relation") or detected.get("intent", {}).get("occasion") in ["gift", "birthday"]:
                    payload["mode"] = "gifting_genius"
                    # map intent fields to recommendation-specific fields
                    if detected.get("intent", {}).get("recipient_relation"):
                        payload["recipient_relation"] = detected["intent"].get("recipient_relation")
                    if detected.get("intent", {}).get("gender"):
                        payload["recipient_gender"] = detected["intent"].get("gender")
                    if detected.get("intent", {}).get("occasion"):
                        payload["occasion"] = detected["intent"].get("occasion")
                logger.info(f"Calling recommendation service with payload: {payload}")
                try:
                    resp = requests.post("http://localhost:8004/recommend", json=payload, timeout=6)
                    logger.info(f"Recommendation service responded: {resp.status_code} - {resp.text[:300]}")
                    if resp.status_code == 200:
                        data = resp.json()
                        # If recommendations list is empty, ask user to broaden criteria
                        items = data.get("recommended_products", [])
                        if not items:
                            reply_text = "I couldn't find any recommendations for those preferences. Could you share your size, preferred brands, or relax the budget?"
                            metadata.update({"recommendation": data, "note": "empty_results"})
                        else:
                            # Build human friendly reply
                            reasons = data.get("personalized_reasoning", "Here are some picks for you.")
                            items = items[:3]
                            lines = [reasons, "\nTop picks:"]
                            for p in items:
                                lines.append(f"• {p.get('name')} — ₹{p.get('price')}")
                                if p.get('personalized_reason'):
                                    lines.append(f"  {p.get('personalized_reason')}")

                            reply_text = "\n".join(lines)
                            metadata.update({"recommendation": data})
                    elif resp.status_code == 404:
                        # Customer profile not found — ask user to provide/confirm customer id
                        logger.warning("Recommendation worker: customer profile not found")
                        reply_text = "I couldn't find your customer profile. Could you provide your customer id or phone number so I can personalize recommendations?"
                        metadata.update({"recommendation_error": "customer_not_found"})
                    else:
                        logger.error(f"Recommendation worker returned status {resp.status_code}")
                        reply_text = "Sorry, I couldn't fetch recommendations right now."
                except requests.exceptions.RequestException as e:
                    logger.error(f"Recommendation service call failed: {e}")
                    reply_text = "Sorry, I couldn't fetch recommendations right now."

        elif detected["type"] == "inventory":
            sku = detected["intent"].get("sku") or request.metadata.get("sku")
            if sku:
                # normalize SKU token: strip punctuation/whitespace and uppercase
                sku_clean = sku.split()[-1]
                sku_clean = re.sub(r"[^A-Za-z0-9]", "", sku_clean).upper()
                logger.info(f"Checking inventory for SKU: {sku_clean}")
                resp = requests.get(f"http://localhost:8001/inventory/{sku_clean}", timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    reply_text = f"Stock for {sku_clean}: online {data.get('online_stock')}, total {data.get('total_stock')}"
                    metadata.update({"inventory": data})
                else:
                    reply_text = "I couldn't find inventory info for that SKU."
            else:
                reply_text = "Which product SKU would you like me to check?"

        elif detected["type"] == "payment":
            # Use payment worker to simulate a payment (demo)
            payload = {
                "user_id": request.metadata.get("user_id", "user_001"),
                "amount": request.metadata.get("amount", 0.0),
                "payment_method": request.metadata.get("payment_method", "upi"),
                "order_id": request.metadata.get("order_id")
            }
            # Validate amount before calling payment service
            if not payload["amount"] or payload["amount"] <= 0:
                reply_text = "I don't have an order amount to process payment. Please provide the amount you'd like to pay."
            else:
                logger.info(f"Calling payment service with payload: {payload}")
                try:
                    resp = requests.post("http://localhost:8003/payment/process", json=payload, timeout=6)
                    if resp.status_code == 200:
                        data = resp.json()
                        reply_text = f"Payment {'succeeded' if data.get('success') else 'failed'}: {data.get('message')}"
                        metadata.update({"payment": data})
                    else:
                        logger.error(f"Payment service returned status {resp.status_code}: {resp.text}")
                        reply_text = "Payment service is unavailable right now. Please try again later or provide payment details."
                except requests.exceptions.RequestException as e:
                    logger.error(f"Payment service call failed: {e}")
                    reply_text = "Payment service is unavailable right now. Please try again later."

        else:
            # Fallback to engine/LLM or simple echo
            reply_text = f"I heard: '{request.message}'. How can I help further?"

    except requests.exceptions.RequestException as e:
        logger.error(f"Worker call failed: {e}")
        reply_text = "Sorry, an internal service is unavailable. Please try again later."

    response = AgentResponse(
        reply=reply_text or "",
        session_token=session_token,
        timestamp=datetime.utcnow().isoformat(),
        metadata=metadata
    )

    logger.info(f"Responding for session: {session_token}")

    return response


@app.post("/api/resume_session", response_model=AgentResponse)
async def resume_session(request: ResumeSessionRequest):
    """
    Resume an existing conversation session
    
    This is a placeholder endpoint that simulates session resumption.
    In production, this would load conversation history and context.
    """
    logger.info(f"Resuming session: {request.session_token}")
    
    # Dummy session resumption logic
    response = AgentResponse(
        reply=f"Welcome back! Your session {request.session_token} has been resumed. How can I assist you today?",
        session_token=request.session_token,
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "agent_type": "sales",
            "session_resumed": True,
            "original_metadata": request.metadata
        }
    )
    
    logger.info(f"Session resumed successfully: {request.session_token}")
    
    return response


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="info"
    )
