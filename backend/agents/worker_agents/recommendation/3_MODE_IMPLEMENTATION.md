# 3-Mode Intelligent Recommendation Agent

## ✅ Implementation Complete

The Recommendation Agent has been upgraded to support **3 distinct modes** without breaking any existing code.

---

## 🎯 Mode Overview

### 1️⃣ **NORMAL MODE** (`mode="normal"`)
**Use Case:** Casual shopping, category browsing, budget-based suggestions

**Features:**
- Filters by category, gender, price range, occasion
- Ranks by rating, brand affinity, purchase frequency
- Real-time inventory checking
- Personalized reasons based on customer history

**Example Request:**
```json
{
  "customer_id": "104",
  "mode": "normal",
  "intent": {
    "category": "Footwear",
    "occasion": "casual",
    "budget_max": 5000
  },
  "limit": 3
}
```

**Example Output Reason:**
```
"You've loved Reebok products before, and this Nike Navy Casual Shoes has an excellent 4.7⭐ rating — available in your Bangalore store right now."
```

---

### 2️⃣ **GIFTING GENIUS MODE** (`mode="gifting_genius"`)
**Use Case:** Emotion + context driven gifting with recipient analysis

**Features:**
- Recipient gender matching (overrides customer gender)
- Interest-based filtering (colors, keywords)
- Safe size options (Accessories, Bags prioritized)
- Auto-generated gift messages
- Gift suitability tags (Birthday/Anniversary/Festive)

**Example Request:**
```json
{
  "customer_id": "104",
  "mode": "gifting_genius",
  "recipient_relation": "wife",
  "recipient_gender": "Female",
  "age_range": "25-35",
  "interests": ["blue", "elegant"],
  "occasion": "birthday",
  "intent": {
    "budget_min": 2000,
    "budget_max": 4000
  },
  "preferred_brands": ["Allen Solly", "Van Heusen"],
  "safe_sizes_only": true,
  "limit": 3
}
```

**Example Output:**
```json
{
  "sku": "SKU000123",
  "personalized_reason": "Since your wife loves blue/elegant, this Allen Solly sling bag is both practical and personal, perfect for birthday",
  "gift_message": "Happy Birthday! Hope you love this Allen Solly Bag as much as I love you!",
  "gift_suitability": "Birthday"
}
```

---

### 3️⃣ **TRENDSEER MODE** (`mode="trendseer"`)
**Use Case:** Predictive fashion oracle - proactive personal styling

**Features:**
- Builds style profile from purchase history (brands, colors, categories)
- Detects trending items from recent order frequency
- Predicts what customer will need next
- Matches favorite colors and price range
- Seasonal awareness

**Example Request:**
```json
{
  "customer_id": "104",
  "mode": "trendseer",
  "limit": 5
}
```

**Example Output Reason:**
```
"You usually love Van Heusen and refresh Shirts regularly — this pastel Van Heusen Oxford Shirt is trending this month and matches your preferences."
```

---

## 🔧 Technical Implementation

### Code Structure
```
app.py
├── Mode Routing (Line ~960)
│   ├── if mode == "gifting_genius" → mode_gifting_genius()
│   ├── elif mode == "trendseer" → mode_trendseer()
│   └── else → mode_normal_recommendations()
│
├── Mode Functions (Lines 560-900)
│   ├── mode_normal_recommendations()
│   ├── mode_gifting_genius()
│   └── mode_trendseer()
│
└── Helper Functions
    ├── generate_gift_reason()
    ├── generate_gift_message()
    ├── map_occasion_to_tag()
    └── generate_predictive_reason()
```

### Gender Matching Logic
All modes properly handle gender filtering:

**Normal Mode:** 
- Checks intent.gender first, then customer.gender
- Supports gift scenarios

**Gifting Genius:**
- Uses recipient_gender explicitly
- Filters by gender column + ProductDisplayName keywords
- Gender keywords: ['men', 'man', 'male', 'boys'] / ['women', 'woman', 'female', 'girls']

**TrendSeer:**
- Inherits customer's gender from profile
- Respects past purchase patterns

---

## 📊 Data Sources Used

All modes leverage:
- ✅ `products.csv` - 902 products with ratings, prices, brands
- ✅ `customers.csv` - 350 customers with loyalty tiers, gender, history
- ✅ `orders.csv` - 910 orders for trend detection
- ✅ `inventory.csv` - 4510 inventory records for availability

---

## 🚀 Testing

### Quick Test
```bash
# Make executable
chmod +x test_3_modes.sh

# Run all 3 modes
./test_3_modes.sh
```

### Individual Mode Tests
```bash
# Normal Mode
curl -X POST http://localhost:8004/recommend -H "Content-Type: application/json" \
-d '{"customer_id":"104","mode":"normal","intent":{"category":"Footwear"},"limit":3}' | python3 -m json.tool

# Gifting Genius
curl -X POST http://localhost:8004/recommend -H "Content-Type: application/json" \
-d '{"customer_id":"104","mode":"gifting_genius","recipient_gender":"Female","occasion":"birthday","intent":{"budget_max":4000},"safe_sizes_only":true,"limit":3}' | python3 -m json.tool

# TrendSeer
curl -X POST http://localhost:8004/recommend -H "Content-Type: application/json" \
-d '{"customer_id":"104","mode":"trendseer","limit":5}' | python3 -m json.tool
```

---

## ✅ Deliverable Checklist

- ✅ 3 modes implemented with clear separation
- ✅ Every recommendation returns `{sku, score, personalized_reason}`
- ✅ Gender matching works across all modes
- ✅ No breaking changes to existing agents
- ✅ No new database schemas
- ✅ Production-ready code (no placeholders)
- ✅ LangChain/LangGraph compatible (internal routing only)
- ✅ Gift bundles capability (Gifting Genius)
- ✅ Trend detection from order frequency (TrendSeer)
- ✅ Style profile extraction (TrendSeer)

---

## 🎯 Sales Agent Integration

The Sales Agent should call with mode parameter:

```python
from typing import Literal

def call_recommendation_agent(
    customer_id: str,
    mode: Literal["normal", "gifting_genius", "trendseer"],
    **kwargs
):
    payload = {
        "customer_id": customer_id,
        "mode": mode,
        **kwargs
    }
    
    response = requests.post(
        "http://localhost:8004/recommend",
        json=payload
    )
    
    return response.json()
```

**Detection Logic:**
- User asks for "gift", "present", "for my wife" → `mode="gifting_genius"`
- User wants proactive suggestions, "what's trending" → `mode="trendseer"`
- Default casual shopping → `mode="normal"`

---

## 📝 Notes

- All three modes respect inventory availability
- LLM-powered reasoning (Gemini/Groq) enhances all modes
- Fallback to template-based reasoning if LLM unavailable
- No modification to Payment/Inventory/Loyalty/Fulfillment agents
- Clean separation of concerns - each mode is self-contained

---

**Status:** ✅ Production Ready
**Version:** 2.0.0 (3-Mode Upgrade)
**Port:** 8004
