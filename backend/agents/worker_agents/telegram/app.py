# Telegram Agent - FastAPI Server
# Handles Telegram bot interactions and forwards to Sales Agent
# Endpoints: POST /telegram/webhook (for Telegram webhooks)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import requests
import logging
import os
from typing import Optional, Dict, Any
import json
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import os

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

# Absolute path to project root
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

CUSTOMERS_CSV = os.path.join(BASE_DIR, "data", "customers.csv")

app = FastAPI(
    title="Telegram Agent",
    description="Telegram bot integration for customer interactions",
    version="1.0.0"
)

# Pending messages storage (chat_id -> message)
pending_messages = {}

# Chat to customer mapping (chat_id -> customer_id)
chat_customer_map = {}

# Data API URL
DATA_API_URL = os.getenv("DATA_API_URL", "http://localhost:8007")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SALES_AGENT_URL = os.getenv("SALES_AGENT_URL", "http://localhost:8010")
SESSION_MANAGER_URL = os.getenv("SESSION_MANAGER_URL", "http://localhost:8000")

# Telegram API base URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class TelegramMessage(BaseModel):
    """Telegram message structure"""
    class Config:
        extra = "ignore"  # Ignore extra fields

    message_id: Optional[int] = None
    from_user: Optional[Dict[str, Any]] = Field(default=None, alias="from")
    chat: Optional[Dict[str, Any]] = None
    date: Optional[int] = None
    text: Optional[str] = None

class TelegramUpdate(BaseModel):
    """Telegram update structure"""
    class Config:
        extra = "ignore"  # Ignore extra fields

    update_id: Optional[int] = None
    message: Optional[TelegramMessage] = None

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

async def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Get customer data by phone number"""
    logger.info(f"🔍 Looking up phone: {phone}")
    try:
        # Load customers from CSV using absolute path
        logger.info(f"📁 Loading CSV from: {CUSTOMERS_CSV}")
        customers_df = pd.read_csv(CUSTOMERS_CSV)
        logger.info(f"📊 CSV loaded, shape: {customers_df.shape}")
        
        # Check if 'phone_number' column exists
        if 'phone_number' not in customers_df.columns:
            logger.error(f"❌ 'phone_number' column not found in CSV. Columns: {list(customers_df.columns)}")
            return None
        
        # Find customer by phone (convert both to string for comparison)
        customer_row = customers_df[customers_df['phone_number'].astype(str) == phone]
        logger.info(f"🔎 Found {len(customer_row)} matching rows for phone {phone}")
        if not customer_row.empty:
            customer = customer_row.iloc[0].to_dict()
            logger.info(f"✅ Found customer: {customer.get('name')} (ID: {customer.get('customer_id')})")
            return customer
        logger.info(f"❌ No customer found for phone {phone}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to get customer by phone: {e}")
        return None

async def create_session_with_phone(customer_id: str, phone: str) -> Optional[str]:
    """Create or restore session using phone number"""
    try:
        # Try to restore existing session by customer_id
        restore_url = f"{SESSION_MANAGER_URL}/session/restore"
        headers = {"X-Customer-Id": str(customer_id)}

        response = requests.get(restore_url, headers=headers, timeout=5)
        if response.status_code == 200:
            session_data = response.json()
            logger.info(f"✅ Restored session for customer {customer_id}")
            return session_data.get("session_token") or session_data.get("session", {}).get("session_token")

        # Create new session
        start_url = f"{SESSION_MANAGER_URL}/session/start"
        payload = {
            "phone": phone,
            "channel": "telegram",
            "customer_id": str(customer_id)
        }

        response = requests.post(start_url, json=payload, timeout=5)
        response.raise_for_status()

        session_data = response.json()
        session_token = session_data.get("session_token")

        logger.info(f"✅ Created new session for customer {customer_id}: {session_token}")
        return session_token

    except Exception as e:
        logger.error(f"❌ Failed to create session for customer {customer_id}: {e}")
        return None

async def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send a message to Telegram chat"""
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
            # Removed parse_mode to avoid Markdown formatting errors
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        logger.info(f"✅ Sent message to Telegram chat {chat_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send Telegram message: {e}")
        return False

async def get_telegram_chat_info(chat_id: str) -> Optional[Dict[str, Any]]:
    """Get chat information from Telegram"""
    try:
        url = f"{TELEGRAM_API_URL}/getChat"
        payload = {"chat_id": chat_id}

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        return response.json().get("result")

    except Exception as e:
        logger.error(f"❌ Failed to get Telegram chat info: {e}")
        return None

# ==========================================
# SESSION MANAGEMENT
# ==========================================

async def get_or_create_session_token(telegram_chat_id: str, phone_number: Optional[str] = None) -> Optional[str]:
    """Get existing session token for Telegram chat or create new one"""
    try:
        # First, try to find existing session by telegram_chat_id
        restore_url = f"{SESSION_MANAGER_URL}/session/restore"
        headers = {"X-Telegram-Chat-Id": telegram_chat_id}

        response = requests.get(restore_url, headers=headers, timeout=5)

        if response.status_code == 200:
            session_data = response.json()
            logger.info(f"✅ Restored session for Telegram chat {telegram_chat_id}: {session_data}")
            return session_data.get("session", {}).get("session_token") or session_data.get("session_token")

        # If no existing session, create new one
        start_url = f"{SESSION_MANAGER_URL}/session/start"
        payload = {
            "channel": "telegram",
            "telegram_chat_id": telegram_chat_id
        }

        if phone_number:
            payload["phone"] = phone_number

        response = requests.post(start_url, json=payload, timeout=5)
        response.raise_for_status()

        session_data = response.json()
        session_token = session_data.get("session_token")

        logger.info(f"✅ Created new session for Telegram chat {telegram_chat_id}: {session_token}")
        return session_token

    except Exception as e:
        logger.error(f"❌ Failed to get/create session for Telegram chat {telegram_chat_id}: {e}")
        return None

# ==========================================
# MESSAGE PROCESSING
# ==========================================

async def process_telegram_message(telegram_message: TelegramMessage) -> bool:
    """Process incoming Telegram message and forward to Sales Agent"""
    try:
        logger.info(f"🔄 Processing Telegram message: {telegram_message.text[:50]}...")
        
        if not telegram_message.chat or not telegram_message.from_user or not telegram_message.text:
            logger.info(f"⚠️  Ignoring incomplete message")
            return True

        chat_id = str(telegram_message.chat["id"])
        text = telegram_message.text.strip()

        if not text:
            logger.info(f"⚠️  Ignoring empty message from chat {chat_id}")
            return True

        logger.info(f"📨 Telegram message from chat {chat_id}: '{text[:100]}...'")

        # Check if this chat already has a customer associated
        existing_customer_id = chat_customer_map.get(chat_id)
        if existing_customer_id:
            logger.info(f"👤 Using existing customer {existing_customer_id} for chat {chat_id}")
            # Restore session and process message directly
            session_token = await create_session_with_phone(existing_customer_id, None)  # Phone not needed for restore
            if not session_token:
                await send_telegram_message(chat_id, "❌ Session expired. Please enter your phone number again.")
                del chat_customer_map[chat_id]  # Remove invalid mapping
                return True
            
            # Process the message directly with existing customer
            customer_id = existing_customer_id
        else:
            # Check if this is a phone number
            if text.isdigit() and len(text) == 10:
                logger.info(f"📞 Detected phone number: {text}")
                # Process as phone number
                customer = await get_customer_by_phone(text)
                logger.info(f"👤 Customer lookup result: {customer is not None}")
                if customer:
                    logger.info(f"👤 Found customer: {customer.get('name')} (ID: {customer.get('customer_id')})")
                if not customer:
                    logger.info(f"❌ Phone {text} not found in CSV")
                    await send_telegram_message(chat_id, "❌ Phone number not found in our records. Please check and try again.")
                    return True

                customer_id = customer['customer_id']
                session_token = await create_session_with_phone(customer_id, text)
                
                if not session_token:
                    await send_telegram_message(chat_id, "❌ Failed to start session. Please try again.")
                    return True

                # Store the mapping for future messages
                chat_customer_map[chat_id] = customer_id

                # Check for pending message
                pending_text = pending_messages.pop(chat_id, None)
                if pending_text:
                    # Process the pending message
                    text = pending_text
                    logger.info(f"📝 Processing pending message: {text}")
                else:
                    await send_telegram_message(chat_id, f"✅ Welcome {customer.get('name', 'Customer')}! How can I help you today?")
                    return True
            else:
                # Store as pending and ask for phone
                pending_messages[chat_id] = text
                await send_telegram_message(chat_id, "📱 Please enter your phone number to continue:")
                return True

        # At this point, we have session_token and text to process
        # Continue with normal processing...

        # Prepare metadata for Sales Agent
        metadata = {
            "channel": "telegram",
            "telegram_chat_id": chat_id,
            "customer_id": customer_id,
            "phone": text if text.isdigit() and len(text) == 10 else None
        }

        # Forward to Sales Agent
        sales_payload = {
            "message": text,
            "session_token": session_token,
            "metadata": metadata
        }

        logger.info(f"🔄 Forwarding to Sales Agent: {SALES_AGENT_URL}/api/message")
        sales_response = requests.post(
            f"{SALES_AGENT_URL}/api/message",
            json=sales_payload,
            timeout=30
        )

        sales_response.raise_for_status()
        sales_data = sales_response.json()
        logger.info(f"✅ Sales Agent response received")

        # Send agent reply back to Telegram
        agent_reply = sales_data.get("reply", "Sorry, I couldn't process your request.")

        # Handle product cards if present
        cards = sales_data.get("cards", [])
        if cards:
            # Format cards for Telegram (plain text)
            card_text = "\n\n".join([
                f"📦 {card.get('name', 'Product')}\n"
                f"💰 ₹{card.get('price', 'N/A')}\n"
                f"📝 {card.get('personalized_reason', '')}"
                for card in cards[:3]  # Limit to 3 cards
            ])
            agent_reply += f"\n\n{card_text}"

        success = await send_telegram_message(chat_id, agent_reply)

        if success:
            logger.info(f"✅ Processed Telegram message from chat {chat_id}")
        else:
            logger.error(f"❌ Failed to send reply to Telegram chat {chat_id}")

        return success

    except Exception as e:
        logger.error(f"❌ Failed to process Telegram message: {e}")
        try:
            await send_telegram_message(chat_id, "Sorry, I'm having trouble processing your message. Please try again.")
        except:
            pass
        return False

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Telegram Agent",
        "status": "running",
        "version": "1.0.0",
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN)
    }

@app.post("/telegram/webhook")
async def telegram_webhook(update: TelegramUpdate):
    """Handle incoming Telegram updates via webhook"""
    try:
        if not update.message:
            # Ignore non-message updates (edits, etc.)
            return {"status": "ignored"}

        # Process the message
        success = await process_telegram_message(update.message)

        return {"status": "processed" if success else "failed"}

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/telegram/send-message")
async def send_message(chat_id: str, message: str):
    """Manually send a message to a Telegram chat (for testing)"""
    success = await send_telegram_message(chat_id, message)
    return {"success": success}

@app.get("/telegram/chat/{chat_id}")
async def get_chat_info(chat_id: str):
    """Get Telegram chat information"""
    chat_info = await get_telegram_chat_info(chat_id)
    if not chat_info:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat_info

# ==========================================
# BOT SETUP
# ==========================================

@app.post("/telegram/set-webhook")
async def set_webhook(webhook_url: str):
    """Set Telegram webhook URL"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Telegram bot token not configured")

        url = f"{TELEGRAM_API_URL}/setWebhook"
        payload = {
            "url": webhook_url,
            "allowed_updates": ["message"]
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        return result

    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/telegram/get-webhook")
async def get_webhook_info():
    """Get current webhook information"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            raise HTTPException(status_code=500, detail="Telegram bot token not configured")

        url = f"{TELEGRAM_API_URL}/getWebhookInfo"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"❌ Failed to get webhook info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8011)