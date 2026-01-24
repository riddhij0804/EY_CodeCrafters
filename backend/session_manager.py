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

# Load customers.csv to map phone numbers to customer IDs
try:
    data_path = Path(__file__).parent / "data" / "customers.csv"
    customers_df = pd.read_csv(data_path)
    for _, row in customers_df.iterrows():
        phone = str(row['phone_number'])
        customer_id = str(row['customer_id'])
        PHONE_TO_CUSTOMER[phone] = customer_id
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

    Requires phone number for session continuity across channels.
    """
    phone: str = Field(..., description="Phone number as primary identifier")
    channel: str = Field(default="whatsapp", description="Channel: whatsapp or kiosk")
    user_id: Optional[str] = Field(default=None, description="Optional user id to associate with session")


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
    session: Dict[str, Any]


class UpdateSessionResponse(BaseModel):
    """Response model returned after successfully updating a session."""
    session: Dict[str, Any]

# -----------------------------
# Helper functions
# -----------------------------

def _now_iso() -> str:
    """Return the current UTC time as an ISO-formatted string.

    This helps keep timestamps consistent across session objects.
    """
    return datetime.utcnow().isoformat() + "Z"


def generate_session_token() -> str:
    """Generate a secure session token.

    Uses UUID4 hex representation to create a reasonably unique token.
    Returns:
        A string token suitable for use in headers and storage keys.
    """
    # Create a random UUID and return the hex string (32 chars, lower-case)
    token = uuid.uuid4().hex
    return token


def create_session(phone: str, channel: str = "whatsapp", user_id: Optional[str] = None) -> (str, Dict[str, Any]):
    """Create a new session object and store it in the in-memory store.

    The session schema follows the user's requirements:
    - session_id: uuid (persistent for the phone number)
    - phone: phone number as primary identifier
    - channel: whatsapp or kiosk
    - user_id: can be `None` initially
    - data: { cart: [], recent: [], chat_context: [], last_action: None }
    - created_at: session creation timestamp
    - updated_at: last activity timestamp
    - expires_at: 2 hours from creation
    - is_active: session status

    Args:
        phone: Phone number as primary identifier
        channel: Channel type (whatsapp or kiosk)
        user_id: Optional user identifier to attach to the session.

    Returns:
        Tuple of (session_token, session_dict)
    """
    # If phone already has a session token, restore it (no expiry)
    existing_token = PHONE_SESSIONS.get(phone)
    if existing_token and existing_token in SESSIONS:
        existing_session = SESSIONS[existing_token]
        existing_session["channel"] = channel
        existing_session["is_active"] = True
        existing_session["updated_at"] = _now_iso()
        SESSIONS[existing_token] = existing_session
        PHONE_SESSION_IDS[phone] = existing_session["session_id"]
        logger.info(f"Restored session for phone={phone}, channel={channel}, session_id={existing_session['session_id']}")
        return existing_token, existing_session

    # Generate the unique token used by clients to refer to this session
    token = generate_session_token()

    # Persistent session_id per phone (create once and reuse forever)
    session_id = PHONE_SESSION_IDS.get(phone) or str(uuid.uuid4())
    PHONE_SESSION_IDS[phone] = session_id

    # Map phone to customer_id from CSV
    customer_id = PHONE_TO_CUSTOMER.get(phone)
    if customer_id:
        logger.info(f"Mapped phone {phone} to customer_id {customer_id}")
    else:
        logger.warning(f"Phone {phone} not found in customers.csv")
    
    # Build the session payload with the required structure
    session = {
        "session_id": session_id,  # persistent id for the phone
        "phone": phone,  # primary identifier
        "channel": channel,  # current channel
        "user_id": user_id,  # can be None
        "customer_id": customer_id,  # mapped from customers.csv
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

    # Store session in the global in-memory dict
    SESSIONS[token] = session
    PHONE_SESSIONS[phone] = token

    # Log for visibility during development
    logger.info(f"Created new session: token={token}, session_id={session['session_id']}, phone={phone}")

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

@app.post("/session/start", response_model=StartSessionResponse)
async def session_start(request: StartSessionRequest):
    """Start a new session or restore existing session for a phone number.

    The endpoint accepts phone, channel, and optional user_id.
    Returns the session_token and full session object.
    If phone already has an active session, restores it with updated channel.
    """
    # Create or restore session using helper; this stores it in-memory
    token, session = create_session(phone=request.phone, channel=request.channel, user_id=request.user_id)

    # Explicitly return a JSONResponse to ensure consistent JSON outputs
    # Clean up any accidental duplicate entries in chat history before returning
    try:
        _dedupe_chat_context(session)
    except Exception:
        logger.debug("Failed to dedupe chat context on session start", exc_info=True)

    return JSONResponse(status_code=200, content={"session_token": token, "session": session})


@app.get("/session/restore", response_model=RestoreSessionResponse)
async def session_restore(x_session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """Restore a session using the `X-Session-Token` header.

    If the header is missing or the token is invalid, this endpoint returns an HTTP error.
    """
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


# Allow this module to be executed directly for local development
if __name__ == "__main__":
    # Run uvicorn with this module's `app` object
    # Use "__main__:app" when running directly, not "backend.session_manager:app"
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=True)
