"""
Session management module for a multi-channel retail AI system.

This module implements an in-memory session store and three HTTP endpoints:
- POST /session/start   -> create a new session and return a session token
- GET  /session/restore -> retrieve a session using the `X-Session-Token` header
- POST /session/update  -> update session state based on an action

All data is kept in memory (no database). This file is a standalone FastAPI app
so it can be run directly with `uvicorn backend.session_manager:app`.

Every function and major step contains inline comments and docstrings.
"""

# Standard library imports
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# FastAPI imports
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import pandas as pd

from db.repositories.customer_repo import ensure_customer, ensure_customer_record

# Configure a simple logger for this module
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Session Manager", version="1.0.0")

# Add CORS middleware for frontend integration
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Lightweight health endpoint used by orchestrators and frontend probes."""
    try:
        # Basic sanity checks
        samples_loaded = len(PHONE_TO_CUSTOMER) >= 0
        return JSONResponse(status_code=200, content={"status": "healthy", "samples": samples_loaded})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "unhealthy", "error": str(e)})


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled error in session_manager: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error"})

# In-memory session store (mapping session_token -> session dict)
# This satisfies the "no database" requirement; all data is lost on process restart.
SESSIONS: Dict[str, Dict[str, Any]] = {}

# Phone-based mappings
# phone_number -> session_token (for quick lookup)
PHONE_SESSIONS: Dict[str, str] = {}
# phone_number -> persistent session_id (ensures one ID per phone across channels)
PHONE_SESSION_IDS: Dict[str, str] = {}
# phone_number -> customer_id mapping from CSV
PHONE_TO_CUSTOMER: Dict[str, str] = {}

# Telegram-based mappings
# telegram_chat_id -> session_token (for quick lookup)
TELEGRAM_SESSIONS: Dict[str, str] = {}
# telegram_chat_id -> phone_number mapping (for customer lookup)
TELEGRAM_TO_PHONE: Dict[str, str] = {}

# Load customers.csv to map phone numbers to customer IDs
try:
    data_path = Path(__file__).parent / "data" / "customers.csv"
    customers_df = pd.read_csv(data_path)
    for _, row in customers_df.iterrows():
        phone = str(row['phone_number'])
        customer_id = str(row['customer_id'])
        PHONE_TO_CUSTOMER[phone] = customer_id
        digits_only = "".join(ch for ch in phone if ch.isdigit())
        if digits_only:
            PHONE_TO_CUSTOMER[digits_only] = customer_id
    logger.info(f"Loaded {len(PHONE_TO_CUSTOMER)} phone-to-customer mappings")
except Exception as e:
    logger.error(f"Failed to load customers.csv: {e}")
    PHONE_TO_CUSTOMER = {}

# No expiry: sessions remain active unless explicitly ended

# -----------------------------
# Pydantic models for requests
# -----------------------------

class StartSessionRequest(BaseModel):
    """Request model for starting a session.

    Requires either phone number or telegram_chat_id for session continuity across channels.
    """
    phone: Optional[str] = Field(default=None, description="Phone number as primary identifier")
    telegram_chat_id: Optional[str] = Field(default=None, description="Telegram chat ID for Telegram sessions")
    channel: str = Field(default="whatsapp", description="Channel: whatsapp, kiosk, or telegram")
    user_id: Optional[str] = Field(default=None, description="Optional user id to associate with session")
    customer_id: Optional[str] = Field(default=None, description="Customer ID from customers.csv")


class StartSessionResponse(BaseModel):
    """Response model returned after creating a session."""
    session_token: str
    session: Dict[str, Any]


class UpdateSessionRequest(BaseModel):
    """Request model for updating session state.

    `action` must be one of: `add_to_cart`, `view_product`, `chat_message`.
    `payload` is an arbitrary dict that contains data required by the action.
    """
    action: str = Field(..., description="Action type to apply to the session")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action-specific data payload")


class RestoreSessionResponse(BaseModel):
    """Response model returned when restoring a session."""
    session_token: str
    session: Dict[str, Any]


class UpdateSessionResponse(BaseModel):
    """Response model returned after successfully updating a session."""
    session: Dict[str, Any]


class LoginRequest(BaseModel):
    """Request body for logging in customers via the web frontend."""
    customer_id: Optional[str] = Field(default=None, description="Unique customer identifier if already known")
    name: str = Field(..., description="Customer display name")
    age: Optional[int] = Field(default=None, description="Age in years")
    gender: Optional[str] = Field(default=None, description="Gender information")
    phone_number: str = Field(..., description="Primary phone number")
    city: Optional[str] = Field(default=None, description="City or locality")
    channel: str = Field(default="web", description="Channel initiating the login")

# -----------------------------
# Helper functions
# -----------------------------

def _now_iso() -> str:
    """Return the current UTC time as an ISO-formatted string.

    This helps keep timestamps consistent across session objects.
    """
    return datetime.utcnow().isoformat() + "Z"


def _register_phone_mapping(phone: Optional[str], customer_id: Optional[str]) -> None:
    """Store convenient lookups for phone -> customer id."""
    if not phone or not customer_id:
        return

    phone_str = str(phone)
    customer_str = str(customer_id)

    PHONE_TO_CUSTOMER[phone_str] = customer_str
    digits_only = "".join(ch for ch in phone_str if ch.isdigit())
    if digits_only:
        PHONE_TO_CUSTOMER[digits_only] = customer_str


def _sanitize_shipping_address(raw: Any) -> Dict[str, str]:
    """Normalize shipping address payloads coming from chat metadata."""
    if not isinstance(raw, dict):
        return {}

    cleaned: Dict[str, str] = {}
    for key in ("city", "landmark", "building", "building_name"):
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        normalized_key = "building" if key in {"building", "building_name"} else key
        if normalized_key == "building" and "building" in cleaned:
            continue
        cleaned[normalized_key] = text
    return cleaned


def _sync_shipping_address(session: Dict[str, Any], address: Dict[str, str]) -> None:
    """Persist the latest shipping address to Supabase for the active customer."""
    if not address:
        return

    logger.info("Syncing shipping address to Supabase: %s", address)

    phone = session.get("phone") or session.get("customer_profile", {}).get("phone_number")
    if not phone:
        return

    profile_name = None
    profile = session.get("customer_profile")
    if isinstance(profile, dict):
        profile_name = profile.get("name")

    attribute_payload: Dict[str, Any] = {}
    city_value = address.get("city")
    if city_value:
        attribute_payload["city"] = city_value

    try:
        ensure_customer_record(
            phone,
            name=profile_name,
            attributes=attribute_payload or None,
            address=address,
        )
        logger.info("Shipping address sync complete for phone=%s", phone)
    except Exception:
        logger.warning("Failed to sync shipping address for phone=%s", phone, exc_info=True)


def generate_session_token() -> str:
    """Generate a secure session token.

    Uses UUID4 hex representation to create a reasonably unique token.
    Returns:
        A string token suitable for use in headers and storage keys.
    """
    # Create a random UUID and return the hex string (32 chars, lower-case)
    token = uuid.uuid4().hex
    return token


def create_session(
    phone: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    channel: str = "whatsapp",
    user_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    customer_profile: Optional[Dict[str, Any]] = None,
) -> (str, Dict[str, Any]):
    """Create a new session object and store it in the in-memory store.

    The session schema follows the user's requirements:
    - session_id: uuid (persistent for the phone number)
    - phone: phone number as primary identifier (can be None for Telegram-only sessions)
    - telegram_chat_id: Telegram chat ID (can be None for phone-only sessions)
    - channel: whatsapp, kiosk, or telegram
    - user_id: can be `None` initially
    - data: { cart: [], recent: [], chat_context: [], last_action: None }
    - created_at: session creation timestamp
    - updated_at: last activity timestamp
    - expires_at: 2 hours from creation
    - is_active: session status

    Args:
        phone: Phone number as primary identifier (optional)
        telegram_chat_id: Telegram chat ID (optional)
        channel: Channel type (whatsapp, kiosk, telegram)
        user_id: Optional user identifier to attach to the session.

    Returns:
        Tuple of (session_token, session_dict)
    """
    # Validate that at least one identifier is provided
    if not phone and not telegram_chat_id:
        raise ValueError("Either phone or telegram_chat_id must be provided")

    # Determine the primary identifier for session lookup
    primary_id = phone or telegram_chat_id
    # Check for existing session based on the primary identifier
    existing_token = None
    if phone and phone in PHONE_SESSIONS:
        existing_token = PHONE_SESSIONS[phone]
    elif telegram_chat_id and telegram_chat_id in TELEGRAM_SESSIONS:
        existing_token = TELEGRAM_SESSIONS[telegram_chat_id]

    if existing_token and existing_token in SESSIONS:
        existing_session = SESSIONS[existing_token]
        existing_session["channel"] = channel
        existing_session["is_active"] = True
        existing_session["updated_at"] = _now_iso()
        # Update telegram_chat_id if provided and different
        if telegram_chat_id and existing_session.get("telegram_chat_id") != telegram_chat_id:
            existing_session["telegram_chat_id"] = telegram_chat_id
            TELEGRAM_SESSIONS[telegram_chat_id] = existing_token
            if phone:
                TELEGRAM_TO_PHONE[telegram_chat_id] = phone
        if customer_profile:
            existing_session["customer_profile"] = customer_profile
            profile_customer_id = None
            if isinstance(customer_profile, dict):
                profile_customer_id = customer_profile.get("customer_id")
            if profile_customer_id:
                existing_session["customer_id"] = str(profile_customer_id)
                if not existing_session.get("user_id"):
                    existing_session["user_id"] = str(profile_customer_id)
                if phone:
                    _register_phone_mapping(phone, profile_customer_id)
        SESSIONS[existing_token] = existing_session
        logger.info(f"Restored session for {primary_id}, channel={channel}, session_id={existing_session['session_id']}")
        return existing_token, existing_session

    # Generate the unique token used by clients to refer to this session
    token = generate_session_token()

    # For phone-based sessions, use persistent session_id per phone
    # For Telegram-only sessions, create a new session_id
    session_id = None
    if phone:
        session_id = PHONE_SESSION_IDS.get(phone) or str(uuid.uuid4())
        PHONE_SESSION_IDS[phone] = session_id
    else:
        session_id = str(uuid.uuid4())

    if customer_profile and not customer_id:
        profile_customer_id = None
        if isinstance(customer_profile, dict):
            profile_customer_id = customer_profile.get("customer_id")
        if profile_customer_id:
            customer_id = str(profile_customer_id)

    # Map to customer_id from CSV (only if phone is provided and customer_id not provided)
    if not customer_id and phone:
        customer_id = PHONE_TO_CUSTOMER.get(phone)
        if not customer_id:
            digits_only = "".join(ch for ch in str(phone) if ch.isdigit())
            if digits_only:
                customer_id = PHONE_TO_CUSTOMER.get(digits_only)

        if customer_id:
            logger.info(f"Mapped phone {phone} to customer_id {customer_id}")
            _register_phone_mapping(phone, customer_id)
        else:
            logger.warning(f"Phone {phone} not found in customers.csv; ensuring Supabase record")
            try:
                ensured = ensure_customer_record(phone)
            except Exception as exc:
                logger.warning(f"Failed to ensure Supabase customer for phone {phone}: {exc}")
                ensured = None

            if ensured:
                ensured_id = ensured.get("customer_id")
                customer_id = str(ensured_id) if ensured_id is not None else None
                if customer_id:
                    ensured_phone = str(ensured.get("phone_number") or phone)
                    _register_phone_mapping(ensured_phone, customer_id)
                    _register_phone_mapping(phone, customer_id)
                    logger.info(f"Created Supabase customer {customer_id} for phone {ensured_phone}")
    
    # Build the session payload with the required structure
    resolved_user_id = user_id or customer_id
    session = {
        "session_id": session_id,  # persistent id for the phone (or unique for Telegram-only)
        "phone": phone,  # primary identifier (can be None)
        "telegram_chat_id": telegram_chat_id,  # Telegram chat ID (can be None)
        "channel": channel,  # current channel
        "user_id": resolved_user_id,  # can be None
        "customer_id": customer_id,  # mapped from customers.csv (can be None)
        "data": {
            "cart": [],  # list of cart items
            "recent": [],  # recently viewed products
            "chat_context": [],  # chat history between user and agent
            "last_action": None,  # track last action performed
        },
        "created_at": _now_iso(),
        "updated_at": _now_iso(),  # timestamp for last update
        "is_active": True,  # session status
    }

    if customer_profile:
        session["customer_profile"] = customer_profile

    # Store session in the global in-memory dict
    SESSIONS[token] = session

    # Update mappings
    if phone:
        PHONE_SESSIONS[phone] = token
        if customer_id:
            _register_phone_mapping(phone, customer_id)
    if telegram_chat_id:
        TELEGRAM_SESSIONS[telegram_chat_id] = token
        if phone:
            TELEGRAM_TO_PHONE[telegram_chat_id] = phone

    # Log for visibility during development
    logger.info(f"Created new session: token={token}, session_id={session['session_id']}, identifier={primary_id}")

    return token, session


def get_session(token: str) -> Dict[str, Any]:
    """Retrieve a session by its token from the in-memory store.

    Args:
        token: Session token provided by the client.

    Raises:
        HTTPException 404 if session not found.

    Returns:
        The session dictionary if found.
    """
    # Attempt to fetch the session from the global store
    session = SESSIONS.get(token)
    if session is None:
        # Return an HTTP error if the token is unknown
        logger.warning(f"Session token not found: {token}")
        raise HTTPException(status_code=404, detail="Session not found")

    return session


def update_session_state(token: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Apply an action to a session's state and persist it in memory.

    Supported actions:
    - add_to_cart: expects `payload['item']` -> item is appended to `data['cart']`
    - view_product: expects `payload['product_id']` -> appended to `data['recent']`
    - chat_message: expects `payload['message']` -> appended to `data['chat_context']` with timestamp

    Args:
        token: Session token identifying which session to update.
        action: Action string describing the update.
        payload: Action-specific data.

    Returns:
        The updated session dictionary.

    Raises:
        HTTPException 400 for unknown actions or missing payload data.
    """
    # Retrieve the session or raise 404
    session = get_session(token)

    # Shortcut reference to the mutable data sub-dictionary
    data = session["data"]

    # Handle each supported action explicitly
    if action == "add_to_cart":
        # Validate payload contains the expected 'item'
        item = payload.get("item")
        if item is None:
            raise HTTPException(status_code=400, detail="'item' is required for add_to_cart action")

        # Append the item to the cart list
        data["cart"].append(item)
        data["last_action"] = {
            "type": "add_to_cart",
            "item": item,
            "timestamp": _now_iso()
        }

        logger.info(f"Added item to cart for token={token}: {item}")

    elif action == "view_product":
        # Validate payload contains 'product_id' or 'product'
        product = payload.get("product") or payload.get("product_id")
        if product is None:
            raise HTTPException(status_code=400, detail="'product' or 'product_id' is required for view_product action")

        # Keep recent as a simple list; prepend newest views
        data["recent"].insert(0, {"product": product, "viewed_at": _now_iso()})

        # Optionally cap recent history length to avoid memory blowup
        if len(data["recent"]) > 50:
            data["recent"] = data["recent"][:50]

        data["last_action"] = {"type": "view_product", "product": product, "timestamp": _now_iso()}

        logger.info(f"Recorded product view for token={token}: {product}")

    elif action == "chat_message":
        # Validate payload contains 'message'
        message = payload.get("message")
        if message is None:
            raise HTTPException(status_code=400, detail="'message' is required for chat_message action")

        # Record the chat message with a timestamp and optional sender (defaults to 'user')
        sender = payload.get("sender", "user")
        # Allow optional metadata to be stored alongside chat messages
        metadata = payload.get("metadata")

        # Prevent accidental duplicate consecutive messages (same sender + text)
        last_entry = data["chat_context"][-1] if data["chat_context"] else None
        if last_entry and last_entry.get("sender") == sender and last_entry.get("message") == message:
            # Update timestamp on the existing entry instead of appending duplicate
            last_entry["timestamp"] = _now_iso()
            if metadata is not None:
                last_entry["metadata"] = metadata
            logger.debug("Skipped appending duplicate chat message; refreshed timestamp instead.")
        else:
            chat_entry = {"sender": sender, "message": message, "timestamp": _now_iso()}
            if metadata is not None:
                chat_entry["metadata"] = metadata
            data["chat_context"].append(chat_entry)

        if isinstance(metadata, dict):
            shipping_address = _sanitize_shipping_address(metadata.get("shipping_address"))
            if shipping_address:
                data["shipping_address"] = shipping_address
                _sync_shipping_address(session, shipping_address)

        data["last_action"] = {"type": "chat_message", "sender": sender, "timestamp": _now_iso()}

        logger.info(f"Appended chat message for token={token}: sender={sender}")

    else:
        # Unknown action type -> client error
        logger.error(f"Unknown action attempted: {action}")
        # Support a lightweight 'set_user' action to set user_id on the session
        if action == "set_user":
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(status_code=400, detail="'user_id' is required for set_user action")

            session["user_id"] = user_id
            session["updated_at"] = _now_iso()
            SESSIONS[token] = session
            logger.info(f"Set user_id for token={token}: {user_id}")
            return session

        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")

    # Update the session-level timestamp to reflect mutation
    session["updated_at"] = _now_iso()

    # Persist change back to the global store (not strictly necessary for mutable dicts)
    SESSIONS[token] = session

    # Return the updated session
    return session


def _dedupe_chat_context(session: Dict[str, Any]) -> None:
    """Remove consecutive duplicate chat entries (in-place) to keep history clean."""
    ctx = session.get("data", {}).get("chat_context")
    if not ctx or len(ctx) < 2:
        return

    cleaned = [ctx[0]]
    for entry in ctx[1:]:
        last = cleaned[-1]
        if entry.get("sender") == last.get("sender") and entry.get("message") == last.get("message"):
            # skip duplicate
            continue
        cleaned.append(entry)

    session["data"]["chat_context"] = cleaned

# -----------------------------
# API Endpoints
# -----------------------------

@app.post("/session/login")
async def session_login(request: LoginRequest):
    """Create or update a customer record and return an active session."""
    customer_id = (request.customer_id or "").strip() or None

    phone = (request.phone_number or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone_number is required")

    name = (request.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    customer_payload = {
        "name": name,
        "age": request.age if request.age is not None else "",
        "gender": (request.gender or "").strip(),
        "phone_number": phone,
        "city": (request.city or "").strip(),
    }

    if customer_id:
        customer_payload["customer_id"] = customer_id

    try:
        customer_record = ensure_customer(customer_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to persist customer record")
        raise HTTPException(status_code=500, detail="Unable to save customer") from exc

    stored_phone = customer_record.get("phone_number") or phone
    stored_customer_id = customer_record.get("customer_id") or customer_id

    _register_phone_mapping(stored_phone, stored_customer_id)

    try:
        attributes = {
            "age": int(customer_record.get("age")) if customer_record.get("age") else None,
            "gender": customer_record.get("gender") or None,
            "city": customer_record.get("city") or None,
        }
        ensure_customer_record(stored_phone, name=customer_record.get("name"), attributes=attributes)
    except Exception as exc:
        logger.debug("Supabase ensure_customer_record skipped: %s", exc)

    token, session = create_session(
        phone=stored_phone,
        channel=request.channel or "web",
        user_id=str(stored_customer_id),
        customer_id=str(stored_customer_id),
        customer_profile=customer_record,
    )

    try:
        _dedupe_chat_context(session)
    except Exception:
        logger.debug("Failed to dedupe chat context on login", exc_info=True)

    return JSONResponse(status_code=200, content={
        "session_token": token,
        "session": session,
        "customer": customer_record,
    })


@app.post("/session/start", response_model=StartSessionResponse)
async def session_start(request: StartSessionRequest):
    """Start a new session or restore existing session for a phone number or Telegram chat.

    The endpoint accepts phone, telegram_chat_id, channel, and optional user_id.
    Returns the session_token and full session object.
    If identifier already has an active session, restores it with updated channel.
    """
    # Create or restore session using helper; this stores it in-memory
    token, session = create_session(
        phone=request.phone,
        telegram_chat_id=request.telegram_chat_id,
        channel=request.channel,
        user_id=request.user_id,
        customer_id=request.customer_id
    )

    # Explicitly return a JSONResponse to ensure consistent JSON outputs
    # Clean up any accidental duplicate entries in chat history before returning
    try:
        _dedupe_chat_context(session)
    except Exception:
        logger.debug("Failed to dedupe chat context on session start", exc_info=True)

    return JSONResponse(status_code=200, content={"session_token": token, "session": session})


@app.get("/session/restore", response_model=RestoreSessionResponse)
async def session_restore(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    x_telegram_chat_id: Optional[str] = Header(None, alias="X-Telegram-Chat-Id"),
    x_customer_id: Optional[str] = Header(None, alias="X-Customer-Id")
):
    """Restore a session using the `X-Session-Token` header, `X-Telegram-Chat-Id` header, or `X-Customer-Id` header.

    If the headers are missing or the identifiers are invalid, this endpoint returns an HTTP error.
    """
    # Try to restore by session token first
    if x_session_token:
        # Retrieve the session using our helper (raises 404 if not found)
        session = get_session(x_session_token)
        # Return the session inside a JSON response
        return JSONResponse(status_code=200, content={"session_token": x_session_token, "session": session})

    # Try to restore by telegram chat ID
    if x_telegram_chat_id:
        if x_telegram_chat_id in TELEGRAM_SESSIONS:
            token = TELEGRAM_SESSIONS[x_telegram_chat_id]
            session = get_session(token)
            # Return the session inside a JSON response
            return JSONResponse(status_code=200, content={"session_token": token, "session": session})
        else:
            raise HTTPException(status_code=404, detail="Session not found for Telegram chat ID")

    # Try to restore by customer ID
    if x_customer_id:
        # Find session by customer_id
        for token, session in SESSIONS.items():
            if session.get("customer_id") == x_customer_id:
                return JSONResponse(status_code=200, content={"session_token": token, "session": session})
        raise HTTPException(status_code=404, detail="Session not found for Customer ID")

    # No valid identifier provided
    raise HTTPException(status_code=400, detail="Missing X-Session-Token, X-Telegram-Chat-Id, or X-Customer-Id header")
    # Ensure a token was provided by the client
    if not x_session_token:
        raise HTTPException(status_code=400, detail="Missing X-Session-Token header")

    # Retrieve the session using our helper (raises 404 if not found)
    session = get_session(x_session_token)
    # Clean up any accidental duplicate entries in chat history before returning
    try:
        _dedupe_chat_context(session)
    except Exception:
        logger.debug("Failed to dedupe chat context on session restore", exc_info=True)

    # Return the session inside a JSON response
    return JSONResponse(status_code=200, content={"session": session})


@app.post("/session/update", response_model=UpdateSessionResponse)
async def session_update(
    request: UpdateSessionRequest,
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
):
    """Update a session's state based on an action and payload.

    The client must provide the `X-Session-Token` header to identify the session,
    and the request body must contain `action` and a `payload` dict.
    """
    # Validate header presence
    if not x_session_token:
        raise HTTPException(status_code=400, detail="Missing X-Session-Token header")

    # Apply the requested update using our helper function
    updated_session = update_session_state(x_session_token, request.action, request.payload)

    # Return the updated session
    return JSONResponse(status_code=200, content={"session": updated_session})


@app.post("/session/end")
async def session_end(x_session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """End a session by marking it as inactive.

    The session_id persists, and the same phone can restore it later.
    Session remains in memory for 2 hours but is marked inactive.
    """
    # Validate header presence
    if not x_session_token:
        raise HTTPException(status_code=400, detail="Missing X-Session-Token header")

    # Retrieve the session
    session = get_session(x_session_token)

    # Mark session as inactive (but keep it restorable)
    session["is_active"] = False
    session["updated_at"] = _now_iso()
    SESSIONS[x_session_token] = session

    logger.info(f"Session ended: token={x_session_token}, session_id={session['session_id']}")

    return JSONResponse(status_code=200, content={
        "message": "Session ended successfully",
        "session_id": session["session_id"],
        "phone": session["phone"]
    })


# ===================================================================
# Authentication Endpoints (New - for multi-channel auth with passwords)
# ===================================================================

# Import auth manager for password-based authentication
try:
    from auth_manager import (
        create_customer,
        validate_login,
        generate_qr_token,
        verify_qr_token,
        cleanup_expired_qr_tokens,
    )
    AUTH_ENABLED = True
    logger.info("Auth manager loaded successfully - password authentication enabled")
except ImportError as e:
    AUTH_ENABLED = False
    logger.warning(f"Auth manager not available: {e}")


class SignupRequest(BaseModel):
    """Request model for customer signup with password."""
    name: str = Field(..., description="Customer name")
    phone_number: str = Field(..., description="Phone number (must be unique)")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    age: Optional[int] = Field(default=None, ge=0, le=150, description="Age in years")
    gender: Optional[str] = Field(default=None, description="Gender")
    city: Optional[str] = Field(default=None, description="City")
    building_name: Optional[str] = Field(default=None, description="Building name")
    address_landmark: Optional[str] = Field(default=None, description="Address landmark")
    channel: str = Field(default="web", description="Channel: web, whatsapp, kiosk")


class PasswordLoginRequest(BaseModel):
    """Request model for password-based login."""
    phone_number: str = Field(..., description="Phone number")
    password: str = Field(..., description="Password")
    channel: str = Field(default="web", description="Channel: web, whatsapp, kiosk")


class QRInitRequest(BaseModel):
    """Request model for QR code initialization."""
    phone_number: str = Field(..., description="Phone number of logged-in user")


class QRVerifyRequest(BaseModel):
    """Request model for QR code verification."""
    qr_token: str = Field(..., description="QR token from QR code")
    channel: str = Field(default="kiosk", description="Channel: typically kiosk")


@app.post("/auth/signup")
async def auth_signup(request: SignupRequest):
    """Create a new customer account with password.
    
    This endpoint:
    1. Validates that phone number is unique
    2. Creates customer record in CSV with password hash
    3. Creates active session
    4. Returns session token and customer record
    
    Dual-channel support:
    - Web users: Must provide password
    - WhatsApp users: Can still use /session/login (password-less flow)
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=501,
            detail="Password authentication not available. Auth manager not loaded."
        )
    
    # Validate required fields
    phone = (request.phone_number or "").strip()
    password = (request.password or "").strip()
    name = (request.name or "").strip()
    
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    try:
        # Create customer with password
        customer_record = create_customer(
            name=name,
            phone=phone,
            password=password,
            age=request.age,
            gender=request.gender,
            city=request.city,
            building_name=request.building_name,
            address_landmark=request.address_landmark,
        )
        
        customer_id = customer_record.get('customer_id')
        
        # Register phone mapping
        _register_phone_mapping(phone, customer_id)
        
        # Create session
        token, session = create_session(
            phone=phone,
            channel=request.channel,
            user_id=customer_id,
            customer_id=customer_id,
            customer_profile=customer_record,
        )
        
        logger.info(f"Signup successful: customer_id={customer_id}, phone={phone}")
        
        return JSONResponse(status_code=201, content={
            "success": True,
            "message": "Account created successfully",
            "session_token": token,
            "session": session,
            "customer": customer_record,
        })
        
    except ValueError as e:
        # Customer already exists or validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Signup failed")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@app.post("/auth/login")
async def auth_login(request: PasswordLoginRequest):
    """Authenticate with phone number and password.
    
    This endpoint:
    1. Validates phone + password credentials
    2. Retrieves customer record
    3. Creates or restores session
    4. Returns session token
    
    Note: WhatsApp users without passwords should continue using /session/login
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=501,
            detail="Password authentication not available. Auth manager not loaded."
        )
    
    phone = (request.phone_number or "").strip()
    password = (request.password or "").strip()
    
    if not phone or not password:
        raise HTTPException(status_code=400, detail="Phone and password are required")
    
    try:
        # Validate credentials
        success, customer = validate_login(phone, password)
        
        if not success:
            raise HTTPException(status_code=401, detail="Invalid phone number or password")
        
        customer_id = customer.get('customer_id')
        
        # Register phone mapping
        _register_phone_mapping(phone, customer_id)
        
        # Create or restore session
        token, session = create_session(
            phone=phone,
            channel=request.channel,
            user_id=customer_id,
            customer_id=customer_id,
            customer_profile=customer,
        )
        
        logger.info(f"Login successful: customer_id={customer_id}, phone={phone}")
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Login successful",
            "session_token": token,
            "session": session,
            "customer": customer,
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.post("/auth/logout")
async def auth_logout(x_session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """Logout by invalidating the current session token.
    
    This endpoint:
    1. Validates session token
    2. Marks session as inactive
    3. Removes token from lookup tables
    4. Returns success message
    
    Note: Session data is preserved for 2 hours but marked inactive.
    User must login again to get a new token.
    """
    if not x_session_token:
        raise HTTPException(status_code=400, detail="Missing X-Session-Token header")
    
    # Check if session exists
    if x_session_token not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found or already logged out")
    
    session = SESSIONS[x_session_token]
    
    # Mark session as inactive
    session["is_active"] = False
    session["updated_at"] = _now_iso()
    
    # Remove from phone lookup
    phone = session.get("phone")
    if phone and PHONE_SESSIONS.get(phone) == x_session_token:
        del PHONE_SESSIONS[phone]
    
    # Remove from telegram lookup if exists
    telegram_chat_id = session.get("telegram_chat_id")
    if telegram_chat_id and TELEGRAM_SESSIONS.get(telegram_chat_id) == x_session_token:
        del TELEGRAM_SESSIONS[telegram_chat_id]
    
    logger.info(f"Logout successful: token={x_session_token}, phone={phone}")
    
    return JSONResponse(status_code=200, content={
        "success": True,
        "message": "Logged out successfully",
        "session_id": session["session_id"],
    })


@app.post("/auth/qr-init")
async def auth_qr_init(
    request: QRInitRequest,
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
):
    """Generate a QR code token for kiosk authentication.
    
    This endpoint:
    1. Validates user is logged in (via session token)
    2. Generates a secure QR token (expires in 15 minutes)
    3. Returns token for QR code generation
    
    Usage flow:
    1. User logs in on website
    2. User requests QR code
    3. QR code displays token
    4. Kiosk scans QR code
    5. Kiosk calls /auth/qr-verify with token
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=501,
            detail="QR authentication not available. Auth manager not loaded."
        )
    
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Must be logged in to generate QR code")
    
    # Verify session exists and is active
    if x_session_token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    session = SESSIONS[x_session_token]
    
    if not session.get("is_active"):
        raise HTTPException(status_code=401, detail="Session is not active")
    
    phone = request.phone_number.strip()
    customer_id = session.get("customer_id") or session.get("user_id")
    
    if not customer_id:
        raise HTTPException(status_code=400, detail="Customer ID not found in session")
    
    try:
        # Generate QR token
        qr_token = generate_qr_token(phone, customer_id)
        
        # Cleanup expired tokens periodically
        cleanup_expired_qr_tokens()
        
        logger.info(f"QR token generated for customer {customer_id}")
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "qr_token": qr_token,
            "expires_in_seconds": 900,  # 15 minutes
            "customer_id": customer_id,
        })
        
    except Exception as e:
        logger.exception("QR token generation failed")
        raise HTTPException(status_code=500, detail=f"Failed to generate QR token: {str(e)}")


@app.post("/auth/qr-verify")
async def auth_qr_verify(request: QRVerifyRequest):
    """Verify a QR code token and create a kiosk session.
    
    This endpoint:
    1. Validates QR token (checks expiry)
    2. Retrieves customer info from token
    3. Creates new kiosk session
    4. Returns session token for kiosk
    
    Usage flow:
    1. Kiosk scans QR code
    2. Kiosk extracts token from QR
    3. Kiosk calls this endpoint
    4. Kiosk receives session token
    5. Kiosk can now make authenticated requests
    """
    if not AUTH_ENABLED:
        raise HTTPException(
            status_code=501,
            detail="QR authentication not available. Auth manager not loaded."
        )
    
    qr_token = (request.qr_token or "").strip()
    
    if not qr_token:
        raise HTTPException(status_code=400, detail="QR token is required")
    
    try:
        # Verify QR token
        valid, customer_info = verify_qr_token(qr_token)
        
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid or expired QR token")
        
        phone = customer_info['phone']
        customer_id = customer_info['customer_id']
        
        # Retrieve customer record
        from db.repositories.customer_repo import get_customer_by_phone
        try:
            customer_record = get_customer_by_phone(phone)
        except:
            # Fallback: load from CSV
            import pandas as pd
            df = pd.read_csv(Path(__file__).parent / "data" / "customers.csv")
            matches = df[df['phone_number'].astype(str) == str(phone)]
            if len(matches) > 0:
                customer_record = matches.iloc[0].to_dict()
            else:
                customer_record = {"customer_id": customer_id, "phone_number": phone}
        
        # Create kiosk session
        token, session = create_session(
            phone=phone,
            channel=request.channel,
            user_id=customer_id,
            customer_id=customer_id,
            customer_profile=customer_record,
        )
        
        logger.info(f"QR verification successful: customer_id={customer_id}, channel={request.channel}")
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "QR authentication successful",
            "session_token": token,
            "session": session,
            "customer": customer_record,
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("QR verification failed")
        raise HTTPException(status_code=500, detail=f"QR verification failed: {str(e)}")


# Allow this module to be executed directly for local development
if __name__ == "__main__":
    # Run uvicorn with this module's `app` object
    # Use "__main__:app" when running directly, not "backend.session_manager:app"
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True)
