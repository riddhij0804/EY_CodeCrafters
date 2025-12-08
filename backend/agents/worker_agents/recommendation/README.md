# Recommendation Agent - Personalized AI Product Recommendations

🤖 Intelligent product recommendation engine with **LLM-powered personalized reasoning** and cross-sell/upsell capabilities.

## 🚀 Features

- **LLM-Powered Reasoning**: Uses Gemini or Groq (llama-3.3-70b) for truly personalized, natural explanations
- **Gift Mode Support**: Intent gender override for shopping for others (e.g., male buying female products)
- **Personalized Recommendations**: Based on customer profile, purchase history, and intent
- **Smart Filtering**: Gender, category, price range, occasion-based filtering
- **Intelligent Ranking**: Uses ratings, brand loyalty, purchase patterns, loyalty tier
- **Inventory-Aware**: Checks real-time inventory availability
- **Upsell Suggestions**: Premium upgrades (20-80% higher price)
- **Cross-Sell Logic**: Complementary products based on cart items
- **Human-like Reasoning**: Each recommendation has unique, conversational explanations
- **Edge Case Handling**: Fallback to trending items when no matches found

## 📦 Installation

### 1. Dependencies Already Installed

All dependencies are in `backend/requirements.txt`:
```bash
fastapi
uvicorn[standard]
pandas
pydantic
google-generativeai  # For Gemini
groq                 # For Groq
python-dotenv
```

### 2. Get Your LLM API Key

**Option 1: Gemini (Recommended - Free)**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key

**Option 2: Groq (Alternative - Free, Better Rate Limits)**
1. Go to https://console.groq.com/keys
2. Create account and get API key
3. Copy the key
4. Uses llama-3.3-70b-versatile model (14,400 requests/day free tier)

### 3. Configure Environment

Edit `backend/.env` and add:

```env
# Choose LLM provider
LLM_PROVIDER=gemini

# Add your API key
GEMINI_API_KEY=your_actual_api_key_here

# Or use Groq instead
# LLM_PROVIDER=groq
# GROQ_API_KEY=your_groq_api_key_here
```

### 4. Data Files Required

The agent uses these CSV files from `backend/data/`:
- ✅ `merged_products_902_rows.csv` - Product catalog
- ✅ `customers.csv` - Customer profiles
- ✅ `orders.csv` - Order history
- ✅ `inventory_realistic.csv` - Inventory availability

## 🔧 Usage

### Start Server

```bash
cd backend/agents/worker_agents/recommendation
python app.py
```

Server runs on: **http://localhost:8004**

You should see:
```
✅ Using Gemini for personalized reasoning
✅ Loaded 902 products
✅ Loaded 350 customers
INFO:     Uvicorn running on http://0.0.0.0:8004
```

### API Documentation

Interactive API docs: **http://localhost:8004/docs**

## 📡 API Endpoints

### 1. Health Check

```bash
GET http://localhost:8004/
```

**Response:**
```json
{
  "status": "running",
  "service": "Recommendation Agent",
  "version": "1.0.0",
  "products_loaded": 902,
  "customers_loaded": 351
}
```

### 2. Get Recommendations

```bash
POST http://localhost:8004/recommend
```

**Request Body:**
```json
{
  "customer_id": "104",
  "intent": {
    "gender": "female",
    "category": "Footwear",
    "occasion": "casual",
    "budget_min": 1000,
    "budget_max": 5000
  },
  "current_cart_skus": ["SKU000001", "SKU000002"],
  "limit": 5
}
```

**Note:** The `gender` field in intent overrides customer's gender for gift scenarios (e.g., male customer buying female products).
```

**Response:**
```json
{
  "recommended_products": [
    {
      "sku": "SKU000123",
      "name": "Men Navy Casual Shoes",
      "brand": "Reebok",
      "category": "Footwear",
      "subcategory": "Shoes",
      "price": 2693.25,
      "rating": 4.7,
      "in_stock": true,
      "personalized_reason": "Since you've loved Reebok products before, and it has an excellent 4.7★ rating from customers like you, I'm confident you'll love this Men Navy Casual Shoes."
    }
  ],
  "upsell": {
    "sku": "SKU000456",
    "name": "Premium Leather Loafers",
    "brand": "Nike",
    "category": "Footwear",
    "subcategory": "Formal Shoes",
    "price": 5200.00,
    "rating": 4.8,
    "in_stock": true,
    "personalized_reason": "Since you've loved Nike products before, and it's a premium upgrade that complements your style perfectly, I'm confident you'll love this Premium Leather Loafers."
  },
  "cross_sell": {
    "sku": "SKU000789",
    "name": "Leather Belt Brown",
    "brand": "Adidas",
    "category": "Accessories",
    "subcategory": "Belts",
    "price": 899.00,
    "rating": 4.5,
    "in_stock": true,
    "personalized_reason": "Since customers often pair this Belts with items like yours, and it has an excellent 4.5★ rating from customers like you, I'm confident you'll love this Leather Belt Brown."
  },
  "personalized_reasoning": "Hi Krishna! As a Gold member with a taste for quality, I've curated these 5 recommendations based on your past purchases and preferences. They're perfect for casual occasions. Each pick is specially chosen with you in mind!",
  "metadata": {
    "customer_id": "104",
    "loyalty_tier": "Gold",
    "past_purchases_count": 8,
    "intent": {...},
    "timestamp": "2025-12-08T10:30:00.000000"
  }
}
```

## 🧠 Recommendation Algorithm

### 1. **Customer Profiling**
- Extracts: age, gender, loyalty tier, purchase history
- Identifies preferred brands from past orders
- Considers loyalty points and satisfaction level

### 2. **Intent-Based Filtering**
- **Gender**: Filters by product gender attribute
- **Category**: Matches category/subcategory
- **Price Range**: Respects budget constraints
- **Occasion**: (Future: can expand to occasion-specific filtering)

### 3. **Intelligent Ranking**

Scoring formula:
```
Base Score = Rating × 10
+ Brand Loyalty Boost (+15 points if customer bought brand before)
+ Loyalty Tier Boost (Gold: +10, Silver: +5, Bronze: 0)
```

### 4. **Inventory Check**
- Queries `inventory_realistic.csv`
- Checks online + all store locations
- Prioritizes in-stock items
- Shows out-of-stock only if needed

### 5. **Upsell Logic**
- Finds products 20-80% more expensive than recommendations
- Minimum 4.3★ rating
- Same category or complementary
- Positioned as "premium upgrade"

### 6. **Cross-Sell Logic**

Category pairing rules:
- **Footwear** → Apparel, Accessories
- **Apparel** → Footwear, Accessories  
- **Accessories** → Apparel, Footwear
- **Personal Care** → Accessories

### 7. **Personalized Reasoning**

Each recommendation includes context like:
- ✅ "You've loved Reebok products before"
- ✅ "This premium item matches your Gold member status"
- ✅ "Excellent 4.7★ rating from customers like you"
- ✅ "Customers often pair this with items like yours"

## 🎯 Example Usage Scenarios

### Scenario 1: First-time Customer (No Purchase History)
```json
{
  "customer_id": "103",
  "intent": {"category": "Apparel", "budget_max": 3000},
  "current_cart_skus": [],
  "limit": 5
}
```
**Behavior**: Falls back to trending items with high ratings

### Scenario 2: Loyal Customer with History
```json
{
  "customer_id": "104",
  "intent": {"occasion": "party", "budget_min": 2000, "budget_max": 8000},
  "current_cart_skus": ["SKU000001"],
  "limit": 3
}
```
**Behavior**: 
- Recommends based on past brand preferences
- Suggests premium upsell
- Offers complementary cross-sell

### Scenario 3: Budget-Conscious Shopping
```json
{
  "customer_id": "102",
  "intent": {"category": "Footwear", "budget_max": 1500},
  "current_cart_skus": [],
  "limit": 5
}
```
**Behavior**: Focuses on best value-for-money within budget

## 🔗 Integration with Sales Agent

The Sales Agent can call this endpoint to get recommendations:

```python
import requests

response = requests.post(
    "http://localhost:8004/recommend",
    json={
        "customer_id": "104",
        "intent": {
            "category": "Shirts",
            "occasion": "office",
            "budget_max": 3000
        },
        "current_cart_skus": cart_items,
        "limit": 5
    }
)

recommendations = response.json()
```

## 🧪 Testing

### Test with curl:

```bash
# Basic recommendation
curl -X POST http://localhost:8004/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "104",
    "intent": {"category": "Footwear"},
    "current_cart_skus": [],
    "limit": 3
  }'

# With full intent
curl -X POST http://localhost:8004/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "101",
    "intent": {
      "category": "Apparel",
      "occasion": "casual",
      "budget_min": 1000,
      "budget_max": 3000
    },
    "current_cart_skus": ["SKU000001"],
    "limit": 5
  }'
```

## 📊 Edge Cases Handled

1. ✅ **Customer not found**: Returns 404 error
2. ✅ **No matching products**: Falls back to trending items (rating ≥ 4.5)
3. ✅ **Out of stock**: Shows limited out-of-stock if needed
4. ✅ **Empty purchase history**: Uses rating-based recommendations
5. ✅ **Budget too low**: Shows best value items within budget
6. ✅ **No cart items**: Cross-sell returns None

## 🚀 Future Enhancements

- [ ] Collaborative filtering (users with similar taste)
- [ ] Season-based recommendations
- [ ] Real-time trend analysis
- [ ] A/B testing for recommendation strategies
- [ ] LLM integration for natural language reasoning
- [ ] Image similarity matching
- [ ] Recently viewed product tracking

## 📝 Service Architecture

```
Sales Agent (Port 8000)
    ↓
    ↓ HTTP POST /recommend
    ↓
Recommendation Agent (Port 8004)
    ↓
    ↓ Reads CSV data
    ↓
Data Files (backend/data/)
    ├── merged_products_902_rows.csv
    ├── customers.csv
    ├── orders.csv
    └── inventory_realistic.csv
```

## ⚡ Performance

- **Load Time**: ~2-3 seconds (loads all CSVs on startup)
- **Response Time**: ~100-300ms per recommendation request
- **Memory Usage**: ~200-300MB (all data in memory)

## 🔒 Clean Integration

✅ **Does NOT modify**:
- Sales Agent logic
- Inventory Agent
- Payment Agent  
- Loyalty Agent
- Session Manager

✅ **Only adds**:
- New standalone microservice
- New `/recommend` endpoint
- CSV-based recommendation logic

---

**Port**: 8004
**Status**: Production Ready ✅
**Dependencies**: None (uses existing backend dependencies)
