# Sales Agent ↔ Recommendation Agent Integration Guide

Complete guide for integrating the Recommendation Agent into the Sales Agent workflow.

## 📋 Overview

The Recommendation Agent provides intelligent, personalized product recommendations that the Sales Agent can present to customers during conversations.

## 🔌 Integration Methods

### Method 1: Direct HTTP Call (Simple)

Add this function to your Sales Agent:

```python
import requests
from typing import Dict, List, Optional

RECOMMENDATION_SERVICE_URL = "http://localhost:8004"

def get_recommendations(
    customer_id: str,
    category: Optional[str] = None,
    gender: Optional[str] = None,
    occasion: Optional[str] = None,
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    cart_skus: List[str] = None,
    limit: int = 5
) -> Dict:
    """
    Get personalized recommendations from Recommendation Agent
    
    Args:
        customer_id: Customer ID for personalization
        category: Product category filter (e.g., "Footwear", "Apparel")
        gender: Target gender for products (overrides customer's gender for gifts)
        occasion: Shopping occasion (e.g., "casual", "party", "office")
        budget_min: Minimum price filter
        budget_max: Maximum price filter
        cart_skus: List of SKUs in cart for cross-sell
        limit: Number of recommendations (default 5)
    
    Returns:
        Dict with recommended_products, upsell, cross_sell, personalized_reasoning
    """
    
    intent = {}
    if category:
        intent['category'] = category
    if gender:
        intent['gender'] = gender  # For gift scenarios
    if occasion:
        intent['occasion'] = occasion
    if budget_min:
        intent['budget_min'] = budget_min
    if budget_max:
        intent['budget_max'] = budget_max
    
    payload = {
        "customer_id": customer_id,
        "intent": intent,
        "current_cart_skus": cart_skus or [],
        "limit": limit
    }
    
    try:
        response = requests.post(
            f"{RECOMMENDATION_SERVICE_URL}/recommend",
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Recommendation service error: {e}")
        return None
```

### Method 2: Using LangChain Tool (Advanced)

Create a LangChain tool wrapper:

```python
from langchain.tools import tool
from typing import Dict, Any
import requests

@tool
def get_product_recommendations(query: str) -> str:
    """
    Get personalized product recommendations for a customer.
    
    Use this tool when the customer asks for product suggestions,
    shopping recommendations, or wants to see items matching their preferences.
    
    Args:
        query: Natural language query containing customer_id and preferences
              Example: "customer 104 wants casual footwear under 5000"
    
    Returns:
        Formatted recommendation text with products and reasoning
    """
    
    # Parse query (you can enhance this with LLM)
    # For now, simple extraction
    customer_id = extract_customer_id(query)
    category = extract_category(query)
    budget_max = extract_budget(query)
    
    # Call recommendation service
    payload = {
        "customer_id": customer_id,
        "intent": {
            "category": category,
            "budget_max": budget_max
        },
        "current_cart_skus": [],
        "limit": 5
    }
    
    response = requests.post(
        "http://localhost:8004/recommend",
        json=payload,
        timeout=5
    )
    
    if response.status_code != 200:
        return "Sorry, I couldn't fetch recommendations at the moment."
    
    data = response.json()
    
    # Format response for LLM
    result = f"{data['personalized_reasoning']}\n\n"
    result += "Here are my top recommendations:\n\n"
    
    for i, product in enumerate(data['recommended_products'], 1):
        result += f"{i}. {product['name']}\n"
        result += f"   Brand: {product['brand']} | Price: ₹{product['price']:.2f}\n"
        result += f"   Rating: {product['rating']}★ | In Stock: {'Yes' if product['in_stock'] else 'No'}\n"
        result += f"   Why: {product['personalized_reason']}\n\n"
    
    if data['upsell']:
        result += f"\n💎 Premium Pick: {data['upsell']['name']}\n"
        result += f"   ₹{data['upsell']['price']:.2f} | {data['upsell']['rating']}★\n"
        result += f"   {data['upsell']['personalized_reason']}\n"
    
    return result
```

## 🎯 Usage Examples in Sales Agent Flow

### Example 1: Customer Asks for Recommendations

**Customer**: "Can you show me some casual shoes under 3000?"

**Sales Agent Flow**:
```python
# Extract intent from customer message
customer_id = session.get("customer_id")
intent = {
    "category": "Footwear",
    "occasion": "casual",
    "budget_max": 3000
}

# Get recommendations
recommendations = get_recommendations(
    customer_id=customer_id,
    category=intent["category"],
    occasion=intent["occasion"],
    budget_max=intent["budget_max"],
    limit=5
)

# Format response
if recommendations:
    response = recommendations['personalized_reasoning'] + "\n\n"
    
    for product in recommendations['recommended_products'][:3]:
        response += f"• {product['name']} - ₹{product['price']:.2f}\n"
        response += f"  {product['personalized_reason']}\n\n"
    
    # Add to session for cart actions
    session['last_recommendations'] = recommendations['recommended_products']
```

### Example 2: Gift Shopping (Gender Override) 🎁

**Customer**: "I want to buy a gift for my wife, maybe some nice apparel under 5000"

**Sales Agent Flow**:
```python
# Detect gift scenario and extract target gender
customer_id = "104"  # Male customer
target_gender = "female"  # Detected from "wife", "her", "mom", etc.

# Get recommendations with gender override
recommendations = get_recommendations(
    customer_id=customer_id,
    category="Apparel",
    gender=target_gender,  # Override customer's gender
    budget_max=5000,
    limit=5
)

# The service will:
# 1. Detect gift mode (customer is male, looking for female products)
# 2. Filter only female products
# 3. Generate gift-appropriate reasoning
# 4. Log: "🎁 Gift mode: Customer is male, looking for female products"

# Format response with gift context
response = "Here are some great gift options for your wife:\n\n"
for product in recommendations['recommended_products'][:3]:
    response += f"• {product['name']} - ₹{product['price']:.2f}\n"
    response += f"  {product['personalized_reason']}\n\n"
```

**Keywords to detect gift scenarios:**
- "gift for my wife/husband/mom/dad/sister/brother/girlfriend/boyfriend"
- "for her/him"
- "women's/men's [product]" (when customer gender differs)
- "looking for [gender] products"

### Example 3: Proactive Upsell During Checkout

**Scenario**: Customer adds item to cart

**Sales Agent Flow**:
```python
# Customer adds SKU000123 to cart
cart_skus = session.get("cart", [])
cart_skus.append("SKU000123")

# Get cross-sell and upsell
recommendations = get_recommendations(
    customer_id=customer_id,
    cart_skus=cart_skus,
    limit=3
)

if recommendations and recommendations['upsell']:
    upsell = recommendations['upsell']
    
    response = f"Great choice! 👍\n\n"
    response += f"Since you're buying that, you might also love:\n"
    response += f"💎 {upsell['name']} - ₹{upsell['price']:.2f}\n"
    response += f"{upsell['personalized_reason']}\n\n"
    response += "Would you like to add this to your cart?"
```

### Example 3: Smart Greeting with Personalized Picks

**Scenario**: Returning customer starts session

**Sales Agent Flow**:
```python
# Customer logs in
customer_id = authenticate_user()

# Get personalized recommendations immediately
recommendations = get_recommendations(
    customer_id=customer_id,
    limit=3
)

if recommendations:
    greeting = f"Welcome back, {customer_name}! 🎉\n\n"
    greeting += recommendations['personalized_reasoning'] + "\n\n"
    greeting += "Today's picks for you:\n"
    
    for product in recommendations['recommended_products']:
        greeting += f"• {product['name']} - ₹{product['price']:.2f}\n"
```

## 🔄 Complete Integration Flow

```
┌─────────────────┐
│   Customer      │
│   Message       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Sales Agent    │
│  (Port 8000)    │
│                 │
│  Extracts:      │
│  - customer_id  │
│  - intent       │
│  - cart_items   │
└────────┬────────┘
         │
         │ HTTP POST /recommend
         │
         ▼
┌─────────────────┐
│ Recommendation  │
│    Agent        │
│  (Port 8004)    │
│                 │
│  Returns:       │
│  - Products     │
│  - Upsell       │
│  - Cross-sell   │
│  - Reasoning    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Sales Agent    │
│                 │
│  Formats and    │
│  presents to    │
│  customer       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Customer      │
│   Response      │
└─────────────────┘
```

## 📝 Intent Extraction Helpers

Use these helpers to extract intent from natural language:

```python
import re

def extract_customer_id(message: str, session: Dict) -> str:
    """Extract customer ID from message or session"""
    # Check session first
    if 'customer_id' in session:
        return session['customer_id']
    
    # Extract from message
    match = re.search(r'customer[_\s]?(\d+)', message, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None

def extract_category(message: str) -> Optional[str]:
    """Extract product category from message"""
    categories = {
        'shoe': 'Footwear',
        'shoes': 'Footwear',
        'footwear': 'Footwear',
        'sneaker': 'Footwear',
        'boot': 'Footwear',
        'sandal': 'Footwear',
        'shirt': 'Apparel',
        'tshirt': 'Apparel',
        't-shirt': 'Apparel',
        'jeans': 'Apparel',
        'pants': 'Apparel',
        'jacket': 'Apparel',
        'dress': 'Apparel',
        'belt': 'Accessories',
        'watch': 'Accessories',
        'bag': 'Accessories',
        'perfume': 'Personal Care',
        'deodorant': 'Personal Care'
    }
    
    message_lower = message.lower()
    for keyword, category in categories.items():
        if keyword in message_lower:
            return category
    
    return None

def extract_budget(message: str) -> Optional[float]:
    """Extract budget constraint from message"""
    # Pattern: under/below/within/max 5000
    patterns = [
        r'(?:under|below|within|max|maximum|up\s+to)\s+(?:rs\.?|₹)?\s*(\d+)',
        r'(?:rs\.?|₹)\s*(\d+)\s+(?:or\s+)?(?:less|max|maximum)',
        r'budget\s+(?:of\s+)?(?:rs\.?|₹)?\s*(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return None

def extract_occasion(message: str) -> Optional[str]:
    """Extract occasion from message"""
    occasions = {
        'casual': ['casual', 'everyday', 'daily', 'regular'],
        'party': ['party', 'celebration', 'event'],
        'office': ['office', 'work', 'professional', 'formal'],
        'sports': ['sports', 'gym', 'workout', 'running'],
        'wedding': ['wedding', 'marriage', 'ceremony']
    }
    
    message_lower = message.lower()
    for occasion, keywords in occasions.items():
        if any(keyword in message_lower for keyword in keywords):
            return occasion
    
    return None
```

## 🧪 Testing Integration

Test the integration with:

```python
# Test basic call
recommendations = get_recommendations(
    customer_id="104",
    category="Footwear",
    budget_max=5000,
    limit=3
)

print(recommendations['personalized_reasoning'])
for product in recommendations['recommended_products']:
    print(f"- {product['name']}: {product['personalized_reason']}")
```

## 🚨 Error Handling

Always handle errors gracefully:

```python
def safe_get_recommendations(**kwargs):
    """Wrapper with error handling"""
    try:
        response = requests.post(
            "http://localhost:8004/recommend",
            json=kwargs,
            timeout=5
        )
        
        if response.status_code == 404:
            return {"error": "Customer not found"}
        elif response.status_code != 200:
            return {"error": "Service unavailable"}
        
        return response.json()
        
    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to recommendation service"}
    except Exception as e:
        return {"error": str(e)}
```

## 📊 Metrics to Track

Monitor these metrics for optimization:

```python
# Log recommendation calls
logger.info(f"Recommendation called: customer={customer_id}, intent={intent}")

# Track acceptance rate
if customer_adds_to_cart:
    logger.info(f"Recommendation accepted: sku={product['sku']}")

# Monitor response times
start = time.time()
recommendations = get_recommendations(...)
duration = time.time() - start
logger.info(f"Recommendation latency: {duration:.3f}s")
```

## ✅ Integration Checklist

- [ ] Add recommendation service URL to environment config
- [ ] Implement `get_recommendations()` helper function
- [ ] Add intent extraction logic to Sales Agent
- [ ] Format recommendations for natural conversation
- [ ] Handle error cases gracefully
- [ ] Test with various customer profiles
- [ ] Monitor performance and acceptance rates
- [ ] Add logging for debugging

## 🎯 Best Practices

1. **Cache recommendations** for repeated queries within same session
2. **Pre-fetch** recommendations when customer browses categories
3. **A/B test** different recommendation strategies
4. **Track click-through** and conversion rates
5. **Update recommendations** after cart changes
6. **Respect customer privacy** - don't be too pushy with upsells

---

**Service**: Recommendation Agent on Port 8004
**Status**: Ready for Integration ✅
**API Docs**: http://localhost:8004/docs
