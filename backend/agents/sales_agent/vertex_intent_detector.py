"""Vertex AI-powered Intent Detection for Sales Agent.

This module uses Google Vertex AI's Gemini models for advanced intent classification
and entity extraction from user messages. It replaces basic regex-based intent detection
with AI-powered understanding.

Key Features:
- Multi-intent detection (recommendation, inventory, payment, gifting, etc.)
- Entity extraction (product names, SKUs, customer IDs, price ranges, categories)
- Context-aware classification using conversation history
- Fallback to rule-based detection if Vertex AI is unavailable
- Structured output with confidence scores

Dependencies:
    pip install google-cloud-aiplatform vertexai

Environment Variables:
    VERTEX_PROJECT_ID: Google Cloud project ID
    VERTEX_LOCATION: Region (default: us-central1)
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON key

Usage:
    detector = VertexIntentDetector()
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

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False
    logging.warning("Vertex AI SDK not installed. Falling back to rule-based detection.")


logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Supported intent types for sales conversations."""
    RECOMMENDATION = "recommendation"
    INVENTORY = "inventory"
    PAYMENT = "payment"
    GIFTING = "gifting"
    COMPARISON = "comparison"
    TREND = "trend"
    SUPPORT = "support"
    FALLBACK = "fallback"


class VertexIntentDetector:
    """
    Vertex AI-powered intent detection with entity extraction.
    
    Uses Gemini 1.5 Flash for fast, cost-effective intent classification
    with structured JSON output.
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Initialize Vertex AI client.
        
        Args:
            project_id: GCP project ID (defaults to VERTEX_PROJECT_ID env var)
            location: GCP region for Vertex AI endpoint (defaults to VERTEX_LOCATION env var)
            model_name: Gemini model to use (defaults to VERTEX_MODEL env var)
        """
        self.project_id = project_id or os.getenv("VERTEX_PROJECT_ID")
        self.location = location or os.getenv("VERTEX_LOCATION", "us-central1")
        self.model_name = model_name or os.getenv("VERTEX_MODEL", "gemini-2.0-flash-exp")
        self.model = None
        self._initialized = False
        
        # Check if Vertex AI is enabled
        vertex_enabled = os.getenv("VERTEX_ENABLED", "true").lower() == "true"
        
        # Initialize Vertex AI if available and enabled
        if VERTEX_AVAILABLE and self.project_id and vertex_enabled:
            try:
                vertexai.init(project=self.project_id, location=self.location)
                self.model = GenerativeModel(self.model_name)
                self._initialized = True
                logger.info(f"✅ Vertex AI initialized successfully!")
                logger.info(f"   Project: {self.project_id}")
                logger.info(f"   Location: {self.location}")
                logger.info(f"   Model: {self.model_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Vertex AI: {e}")
                logger.error(f"   Falling back to rule-based intent detection")
                self._initialized = False
        else:
            if not vertex_enabled:
                logger.info("ℹ️  Vertex AI disabled via VERTEX_ENABLED=false")
            if not VERTEX_AVAILABLE:
                logger.warning("⚠️  Vertex AI SDK not available - install: pip install google-cloud-aiplatform vertexai")
            if not self.project_id:
                logger.warning("⚠️  VERTEX_PROJECT_ID not set in environment")
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
  "intent": "recommendation|inventory|payment|gifting|comparison|trend|loyalty|social_validation|support|fallback",
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
                "method": "vertex_ai|rule_based"
            }
        """
        # Try Vertex AI first
        if self._initialized and self.model:
            try:
                result = await self._detect_with_vertex(user_message, conversation_history)
                result["method"] = "vertex_ai"
                logger.info(f"Vertex AI intent: {result['intent']} (confidence: {result['confidence']:.2f})")
                return result
            except Exception as e:
                logger.error(f"Vertex AI detection failed: {e}")
                # Fall through to rule-based backup
        
        # Fallback to rule-based detection
        result = self._detect_with_rules(user_message)
        result["method"] = "rule_based"
        logger.info(f"Rule-based intent: {result['intent']}")
        return result
    
    async def _detect_with_vertex(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Use Vertex AI Gemini for intent detection.
        
        Args:
            user_message: User input
            conversation_history: Conversation context
            
        Returns:
            Parsed intent result
        """
        prompt = self._build_intent_prompt(user_message, conversation_history)
        
        # Configure for structured JSON output
        generation_config = GenerationConfig(
            temperature=0.2,  # Low temperature for consistent classification
            top_p=0.8,
            top_k=40,
            max_output_tokens=512,
        )
        
        # Generate response
        response = self.model.generate_content(
            prompt,
            generation_config=generation_config,
        )
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Clean up response (remove markdown code blocks if present)
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            result = json.loads(response_text)
            
            # Validate required fields
            if "intent" not in result:
                raise ValueError("Missing 'intent' field in response")
            
            # Set defaults for missing fields
            result.setdefault("confidence", 0.8)
            result.setdefault("entities", {})
            result.setdefault("reasoning", "")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Vertex AI response as JSON: {response_text}")
            raise ValueError(f"Invalid JSON response from Vertex AI: {e}")
    
    def _detect_with_rules(self, user_message: str) -> Dict[str, Any]:
        """
        Rule-based intent detection as fallback.
        
        This is the original regex-based logic for when Vertex AI is unavailable.
        
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
        elif re.search(r"\b(recommend|suggest|show me|looking for|what are|something like|need|want|interested)\b", text):
            intent = IntentType.RECOMMENDATION
            confidence = 0.8
            
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
                    r"(?:is there|do you have|available)\s+(.+?)\s+(?:in stock|available|stock)",
                    r"(?:check|checking)\s+(?:stock|availability)\s+(?:for|of)\s+(.+?)(?:\?|$)",
                    r"(?:is|are)\s+(.+?)\s+(?:available|in stock)",
                ]
                for pattern in product_patterns:
                    match = re.search(pattern, text)
                    if match:
                        entities["product_name"] = match.group(1).strip()
                        break
        
        # Payment/checkout intent
        elif re.search(r"\b(buy|checkout|order|pay|purchase|place order|proceed)\b", text):
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
        elif re.search(r"\b(loyalty|points|reward|coupon|discount|offer|promo|cashback|redeem)\b", text):
            intent = "loyalty"
            confidence = 0.9
            # Extract coupon code if present
            coupon_match = re.search(r"\b([A-Z]{3,10}\d{1,3})\b", user_message)
            if coupon_match:
                entities["coupon_code"] = coupon_match.group(1)
        
        # Support/help
        elif re.search(r"\b(help|support|problem|issue|return|refund|cancel|complaint)\b", text):
            intent = IntentType.SUPPORT
            confidence = 0.85
        
        # Extract customer ID if present
        customer_match = re.search(r"(?:customer\s*id|memberid|id)\s*[:#]?\s*(\d{2,12})", text, re.IGNORECASE)
        if customer_match:
            entities["customer_id"] = customer_match.group(1)
        
        return {
            "intent": intent.value,
            "confidence": confidence,
            "entities": entities,
            "reasoning": "Rule-based pattern matching"
        }


# Singleton instance for reuse
_detector_instance: Optional[VertexIntentDetector] = None


def get_intent_detector() -> VertexIntentDetector:
    """
    Get or create singleton VertexIntentDetector instance.
    
    Returns:
        Shared VertexIntentDetector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = VertexIntentDetector()
    return _detector_instance


# Convenience function for direct usage
async def detect_intent(
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Detect intent from user message using Vertex AI.
    
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
        detector = VertexIntentDetector()
        
        test_cases = [
            "I want to buy a gift for my mom's birthday under 5000",
            "Show me running shoes",
            "Is SKU12345 available in size 9?",
            "I want to checkout",
            "What are the trending sneakers?",
            "Compare Nike vs Adidas running shoes",
        ]
        
        print("Testing Vertex AI Intent Detection\n" + "="*60)
        for msg in test_cases:
            result = await detector.detect_intent(msg)
            print(f"\nMessage: {msg}")
            print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
            print(f"Entities: {result['entities']}")
            print(f"Method: {result['method']}")
    
    asyncio.run(test_detector())
