# Telegram utilities for the Telegram Agent

import requests
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_BOT_TOKEN else None

def send_message_sync(chat_id: str, text: str) -> bool:
    """Send a message to Telegram chat (synchronous version)"""
    if not TELEGRAM_API_URL:
        logger.error("❌ Telegram bot token not configured")
        return False

    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        logger.info(f"✅ Sent message to Telegram chat {chat_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send Telegram message: {e}")
        return False

def get_bot_info() -> Optional[Dict[str, Any]]:
    """Get information about the bot"""
    if not TELEGRAM_API_URL:
        return None

    try:
        url = f"{TELEGRAM_API_URL}/getMe"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        return response.json().get("result")

    except Exception as e:
        logger.error(f"❌ Failed to get bot info: {e}")
        return None

def validate_token() -> bool:
    """Validate that the bot token is working"""
    bot_info = get_bot_info()
    if bot_info:
        logger.info(f"✅ Telegram bot connected: @{bot_info.get('username')}")
        return True
    else:
        logger.error("❌ Telegram bot token is invalid")
        return False