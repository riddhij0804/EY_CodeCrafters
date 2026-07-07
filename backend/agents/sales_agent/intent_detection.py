"""Groq-powered Intent Detection for Sales Agent.

This module uses Groq's LLM API (Llama models) for advanced intent classification
and entity extraction from user messages. It replaces basic regex-based intent detection
with AI-powered understanding.

Key Features:
- Multi-intent detection (recommendation, inventory, payment, gifting, etc.)
- Entity extraction (product names, SKUs, customer IDs, price ranges, categories)
- Context-aware classification using conversation history
- Fallback to rule-based detection if Groq is unavailable
- Structured output with confidence scores

Dependencies:
    pip install groq

Environment Variables:
    GROQ_API_KEY: Groq API key

Usage:
    detector = GroqIntentDetector()
    result = await detector.detect_intent(
        user_message="I want to buy a gift for my mom's birthday under 5000",
        conversation_history=[...]
    )
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dotenv import load_dotenv
from pathlib import Path

BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(BACKEND_ENV, override=True)

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logging.warning("Groq SDK not installed. Falling back to rule-based detection.")


logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    RECOMMENDATION = "recommendation"
    INVENTORY = "inventory"
    PAYMENT = "payment"
    GIFTING = "gifting"
    COMPARISON = "comparison"
    TREND = "trend"
    AMBIENT_COMMERCE = "ambient_commerce"
    LOYALTY = "loyalty"
    SOCIAL_VALIDATION = "social_validation"
    SUPPORT = "support"
    FALLBACK = "fallback"


class GroqIntentDetector:
    """
    Groq-powered intent detection with entity extraction.

    Uses Llama 3.3 70B Versatile for fast, cost-effective intent classification
    with structured JSON output.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model_name: Groq model to use (defaults to GROQ_MODEL env var)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model_name = model_name or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.client = None
        self._initialized = False

        # Check if Groq is enabled
        groq_enabled = os.getenv("GROQ_ENABLED", "true").lower() == "true"

        # Initialize Groq if available and enabled
        if GROQ_AVAILABLE and self.api_key and groq_enabled:
            try:
                self.client = Groq(api_key=self.api_key)
                self._initialized = True
                logger.info(f"✅ Groq initialized successfully!")
                logger.info(f"   Model: {self.model_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq: {e}")
                logger.error(f"   Falling back to rule-based intent detection")
                self._initialized = False
        else:
            if not groq_enabled:
                logger.info("ℹ️  Groq disabled via GROQ_ENABLED=false")
            if not GROQ_AVAILABLE:
                logger.warning("⚠️  Groq SDK not available - install: pip install groq")
            if not self.api_key:
                logger.warning("⚠️  GROQ_API_KEY not set in environment")
            logger.info("ℹ️  Using rule-based intent detection")

    def _build_intent_prompt(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Construct the prompt for intent detection.

        Args:
            user_message: Current user input
            conversation_history: Previous conversation turns for context

        Returns:
            Formatted prompt string
        """
        # Context from conversation history
        context_block = ""
        if conversation_history:
            recent_turns = conversation_history[-5:]  # Last 5 turns for context
            context_block = "### Conversation Context:\n"
            for turn in recent_turns:
                sender = turn.get("sender", "user")
                msg = turn.get("message", "")
                context_block += f"{sender.upper()}: {msg}\n"
            context_block += "\n"

        prompt = f"""You are an expert intent classifier for a retail sales assistant. Analyze the user's message and extract:

1. PRIMARY INTENT (choose one):
   - recommendation: User wants product suggestions
   - inventory: Checking stock/availability
   - payment: Ready to purchase/checkout
   - gifting: Buying a gift for someone
   - comparison: Comparing multiple products
   - trend: Asking about trends/popular items
    - ambient_commerce: Visual search or image-based product discovery
   - loyalty: Asking about loyalty points, rewards, coupons, offers, discounts
   - social_validation: Asking what others buy/like, community insights, what's popular in their circle
   - support: Help with order/return/issue
   - fallback: Unclear intent

2. ENTITIES (extract all that apply):
   - category: Product category (footwear, apparel, accessories, etc.)
   - subcategory: More specific type (sneakers, jacket, watch, etc.)
   - brand: Brand name mentioned
   - product_name: Full product name mentioned (e.g., "Men Black Flip Flops", "Reestyle Deo")
   - sku: Product SKU code (format: SKU followed by numbers)
   - customer_id: Customer/member ID
   - price_min: Minimum budget
   - price_max: Maximum budget
   - occasion: Shopping occasion (birthday, wedding, gym, office, casual, etc.)
   - recipient_relation: For gifting (mother, father, wife, husband, friend, etc.)
   - gender: Target gender (male, female, unisex)
   - age_group: Target age (kid, teen, adult, senior)
   - style_preference: Style keywords (sporty, formal, casual, trendy, etc.)
   - color: Color preferences
   - size: Size mentioned
   - urgency: Time sensitivity (urgent, today, weekend, no rush)

3. CONFIDENCE SCORE (0.0-1.0): How confident are you about the intent?

{context_block}### Current User Message:
"{user_message}"

### Response Format (valid JSON only):
{{
    "intent": "recommendation|inventory|payment|gifting|comparison|trend|ambient_commerce|loyalty|social_validation|support|fallback",
  "confidence": 0.95,
  "entities": {{
    "category": "footwear",
    "subcategory": "sneakers",
    "price_max": 5000,
    "occasion": "birthday",
    "recipient_relation": "mother",
    "gender": "female"
  }},
  "reasoning": "Brief explanation of classification"
}}

Respond with ONLY the JSON object, no additional text."""

        return prompt

    async def detect_intent(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect intent and extract entities from user message.

        Args:
            user_message: The user's input text
            conversation_history: Previous conversation for context
            metadata: Additional context (user_id, session info, etc.)

        Returns:
            Dict containing:
            {
                "intent": str,
                "confidence": float,
                "entities": dict,
                "reasoning": str,
                "method": "groq|rule_based"
            }
        """
        # Try Groq first
        if self._initialized and self.client:
            try:
                result = await self._detect_with_groq(user_message, conversation_history)
                result["method"] = "groq"
                logger.info(f"Groq detection: {result['intent']} (confidence: {result['confidence']:.2f})")
                return result
            except Exception as e:
                logger.error(f"Groq detection failed: {e}")
                # Fall through to rule-based backup

        # Fallback to rule-based detection
        result = self._detect_with_rules(user_message)
        result["method"] = "rule_based"
        logger.info(f"Rule-based intent: {result['intent']}")
        return result

    async def _detect_with_groq(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Use Groq (Llama 3.3 70B Versatile) for intent detection.

        Args:
            user_message: User input
            conversation_history: Conversation context

        Returns:
            Parsed intent result
        """
        prompt = self._build_intent_prompt(user_message, conversation_history)

        # Generate response using Groq chat completions, with JSON mode if supported
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Some models/deployments may not support response_format - retry without it,
            # relying on strict JSON prompting instead.
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=512,
            )

        # Parse JSON response
        response_text = completion.choices[0].message.content.strip()

        # Clean up response (remove markdown code blocks if present)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            # Try to fix common JSON issues
            fixed_text = response_text

            # Remove trailing commas before closing braces/brackets
            fixed_text = re.sub(r',\s*([}\]])', r'\1', fixed_text)

            # Add missing closing braces if needed
            open_braces = fixed_text.count('{')
            close_braces = fixed_text.count('}')
            if open_braces > close_braces:
                fixed_text += '}' * (open_braces - close_braces)

            result = json.loads(fixed_text)

            # Validate required fields
            if "intent" not in result:
                raise ValueError("Missing 'intent' field in response")

            # Set defaults for missing fields
            result.setdefault("confidence", 0.8)
            result.setdefault("entities", {})
            result.setdefault("reasoning", "")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq response as JSON: {response_text}")
            raise ValueError(f"Invalid JSON response from Groq: {e}")

    def _detect_with_rules(self, user_message: str) -> Dict[str, Any]:
        """
        Rule-based intent detection as fallback.

        This is the original regex-based logic for when Groq is unavailable.

        Args:
            user_message: User input text

        Returns:
            Intent detection result
        """
        text = user_message.lower()
        intent = IntentType.FALLBACK
        entities = {}
        confidence = 0.6

        # Gifting intent (highest priority)
        if re.search(r"\b(gift|present|for my|for her|for him|wife|husband|mom|mother|dad|father|birthday|anniversary)\b", text):
            intent = IntentType.GIFTING
            confidence = 0.85

            # Extract occasion
            if re.search(r"\bbirthday\b", text):
                entities["occasion"] = "birthday"
            elif re.search(r"\banniversary\b", text):
                entities["occasion"] = "anniversary"
            elif re.search(r"\b(wedding|marriage)\b", text):
                entities["occasion"] = "wedding"
            else:
                entities["occasion"] = "gift"

            # Extract recipient
            if re.search(r"\b(mom|mother|mum)\b", text):
                entities["recipient_relation"] = "mother"
                entities["gender"] = "female"
            elif re.search(r"\b(dad|father|papa)\b", text):
                entities["recipient_relation"] = "father"
                entities["gender"] = "male"
            elif re.search(r"\b(wife|spouse)\b", text):
                entities["recipient_relation"] = "wife"
                entities["gender"] = "female"
            elif re.search(r"\b(husband)\b", text):
                entities["recipient_relation"] = "husband"
                entities["gender"] = "male"
            elif re.search(r"\b(sister)\b", text):
                entities["recipient_relation"] = "sister"
                entities["gender"] = "female"
            elif re.search(r"\b(brother)\b", text):
                entities["recipient_relation"] = "brother"
                entities["gender"] = "male"

        # Recommendation intent
            elif re.search(
                r"\b(recommend|suggest|show me|show|find|looking for|what are|something like|need|want|interested|buy|purchase|search)\b",
                text
            ):          
                intent = IntentType.RECOMMENDATION
                confidence = 0.8

            elif re.search(
                r"\b(popular|trending|what are people buying|best seller|bestseller|community|liked by others|most bought|viral)\b",
                text
            ):
                intent = IntentType.SOCIAL_VALIDATION
                confidence = 0.9
            # Extract category
            cat_match = re.search(r"\b(footwear|shoes|sneaker|apparel|clothes|clothing|jacket|shirt|pants|accessories|watch|bag|belt)\b", text)
            if cat_match:
                entities["category"] = cat_match.group(1).capitalize()

            # Extract budget
            budget_match = re.search(r"under\s*(?:rs|₹|inr)?\s*(\d{3,6})", text)
            if budget_match:
                entities["price_max"] = int(budget_match.group(1))

            # Extract style preferences
            if re.search(r"\b(sport|athletic|gym|running)\b", text):
                entities["style_preference"] = "sporty"
            elif re.search(r"\b(formal|office|business)\b", text):
                entities["style_preference"] = "formal"
            elif re.search(r"\b(casual|everyday)\b", text):
                entities["style_preference"] = "casual"

        # Inventory check
        elif re.search(r"\b(in stock|available|stock|availability|is there|do you have)\b", text):
            intent = IntentType.INVENTORY
            confidence = 0.9

            # Extract SKU
            sku_match = re.search(r"\b(SKU\d{3,6})\b", user_message, re.IGNORECASE)
            if sku_match:
                entities["sku"] = sku_match.group(1).upper()
            else:
                # Extract product name from the message
                # Pattern: "is there [product name] in stock" or "do you have [product name]"
                product_patterns = [
                    r"are\s+(.+?)\s+available",
                    r"is\s+(.+?)\s+available",
                    r"do you have\s+(.+)",
                    r"is there\s+(.+)",
                    r"(.+?)\s+in stock",
                    r"availability of\s+(.+)",
                    r"stock of\s+(.+)",
                ]
                for pattern in product_patterns:
                    match = re.search(pattern, text)
                    if match:
                        entities["product_name"] = match.group(1).strip()
                        break

        # Visual search / ambient commerce intent
        elif re.search(r"\b(visual search|search by image|search by photo|image search|photo search|upload image|upload photo|scan image|scan photo|camera search|find similar from image)\b", text):
            intent = IntentType.AMBIENT_COMMERCE
            confidence = 0.92

        # Order tracking / support (route to fulfillment)
        elif re.search(r"\b(where is my order|order status|track order|track my order|where is order)\b", text):
            intent = IntentType.SUPPORT
            confidence = 0.95
            # Extract order id patterns like ORD000894 or ORD-XXXX or ORD-123456
            # Must have at least one digit or special char after ORD to distinguish from word "order"
            oid_match = re.search(r"\b(ORD(?:[-_]?\d+[-\w]*|[-_]\w+))\b", user_message, re.IGNORECASE)
            if oid_match:
                matched_id = oid_match.group(1).upper()
                entities["order_id"] = matched_id
                logger.debug(f"Extracted order_id: {matched_id}")

        # Payment/checkout intent (avoid matching pure tracking queries)
        elif re.search(r"\b(buy|checkout|pay|purchase|place order|proceed)\b", text):
            intent = IntentType.PAYMENT
            confidence = 0.9

        # Comparison intent
        elif re.search(r"\b(compare|difference|between|versus|vs|which is better)\b", text):
            intent = IntentType.COMPARISON
            confidence = 0.85

        # Trend inquiry
        elif re.search(r"\b(trend|trending|popular|bestseller|top rated|what's hot)\b", text):
            intent = IntentType.TREND
            confidence = 0.85

        # Loyalty/rewards intent
        elif re.search(
            r"\b(loyalty|points|reward|rewards|coupon|discount|offer|offers|promo|cashback|redeem|tier|membership|status)\b",
            text
        ):
            intent = IntentType.LOYALTY
            confidence = 0.95
            # Extract coupon code if present
            coupon_match = re.search(r"\b([A-Z]{3,10}\d{1,3})\b", user_message)
            if coupon_match:
                entities["coupon_code"] = coupon_match.group(1)

        # Support/help
        # Support/help (generic)
        elif re.search(r"\b(help|support|problem|issue|return|refund|cancel|complaint)\b", text):
            intent = IntentType.SUPPORT
            confidence = 0.85
            # Try extracting order id if present (must have digit or special char after ORD)
            oid_match = re.search(r"\b(ORD(?:[-_]?\d+[-\w]*|[-_]\w+))\b", user_message, re.IGNORECASE)
            if oid_match:
                matched_id = oid_match.group(1).upper()
                entities["order_id"] = matched_id
                logger.debug(f"Extracted order_id: {matched_id}")

        # If still fallback but order ID is present, route to support
        if intent == IntentType.FALLBACK:
            oid_match = re.search(r"\b(ORD(?:[-_]?\d+[-\w]*|[-_]\w+))\b", user_message, re.IGNORECASE)
            if oid_match:
                matched_id = oid_match.group(1).upper()
                entities["order_id"] = matched_id
                intent = IntentType.SUPPORT
                confidence = 0.8
            else:
                numeric_match = re.search(r"(?:order\s*id|orderid|order-id)\s*[:#-]?\s*(\d{3,})", text, re.IGNORECASE)
                if numeric_match:
                    entities["order_id"] = numeric_match.group(1)
                    intent = IntentType.SUPPORT
                    confidence = 0.75

        # Extract customer ID if present
        customer_match = re.search(r"(?:customer\s*id|memberid|id)\s*[:#]?\s*(\d{2,12})", text, re.IGNORECASE)
        if customer_match:
            entities["customer_id"] = customer_match.group(1)

        return {
            "intent": intent.value if isinstance(intent, IntentType) else intent,
            "confidence": confidence,
            "entities": entities,
            "reasoning": "Rule-based pattern matching"
        }


# Singleton instance for reuse
_detector_instance: Optional[GroqIntentDetector] = None


def get_intent_detector() -> GroqIntentDetector:
    """
    Get or create singleton GroqIntentDetector instance.

    Returns:
        Shared GroqIntentDetector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = GroqIntentDetector()
    return _detector_instance


# Convenience function for direct usage
async def detect_intent(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detect intent from user message using Groq.

    Args:
        user_message: User's input text
        conversation_history: Previous conversation turns
        metadata: Additional context

    Returns:
        Intent detection result with entities

    Example:
        >>> result = await detect_intent("I need running shoes under 3000")
        >>> print(result['intent'])  # "recommendation"
        >>> print(result['entities'])  # {"category": "footwear", "price_max": 3000}
    """
    detector = get_intent_detector()
    return await detector.detect_intent(user_message, conversation_history, metadata)


if __name__ == "__main__":
    """Test the intent detector with sample messages."""
    import asyncio

    async def test_detector():
        detector = GroqIntentDetector()

        test_cases = [
            "I want to buy a gift for my mom's birthday under 5000",
            "Show me running shoes",
            "Is SKU12345 available in size 9?",
            "I want to checkout",
            "What are the trending sneakers?",
            "Compare Nike vs Adidas running shoes",
        ]

        print("Testing Groq Intent Detection\n" + "="*60)
        for msg in test_cases:
            result = await detector.detect_intent(msg)
            print(f"\nMessage: {msg}")
            print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
            print(f"Entities: {result['entities']}")
            print(f"Method: {result['method']}")

    asyncio.run(test_detector())