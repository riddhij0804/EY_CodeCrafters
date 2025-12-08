# Post-Purchase Stylist Agent

**Groq AI-powered** styling recommendations using Llama 3.1 70B - Lightning-fast, personalized suggestions based on actual purchase.

## Main Endpoints

### 1. Outfit Suggestions (AI-Generated)
```bash
POST /stylist/outfit-suggestions
{
  "user_id": "user123",
  "product_sku": "SKU000001",
  "product_name": "Black Sequined Skirt",
  "category": "skirt",
  "color": "black",
  "brand": "Zara"
}
```

### 2. Care Instructions
```bash
POST /stylist/care-instructions
{
  "product_sku": "SKU000015",
  "material": "linen"
}
```

### 3. Occasion Styling (AI-Generated)
```bash
POST /stylist/occasion-styling
{
  "user_id": "user123",
  "product_sku": "SKU000020",
  "product_name": "White Formal Shirt"
}
```

### 4. Seasonal Styling (AI-Generated)
```bash
POST /stylist/seasonal-styling
{
  "product_sku": "SKU000025",
  "product_name": "Denim Jacket",
  "product_type": "jacket"
}
```

### 5. Fit Feedback
```bash
POST /stylist/fit-feedback
{
  "user_id": "user123",
  "product_sku": "SKU000030",
  "size_purchased": "M",
  "fit_rating": "too_tight",
  "length_feedback": "perfect",
  "comments": "Great quality but size runs small"
}
```

## Features

✅ **Groq AI Outfit Suggestions** - Llama 3.1 70B creates personalized recommendations (⚡ 10x faster)
✅ Material-specific care instructions
✅ **Groq AI Occasion Styling** (Office, Casual, Party)
✅ **Groq AI Seasonal Styling** tips
✅ Fit feedback for future size recommendations

**Note:** Complementary items/cross-sell feature removed - all recommendations are AI-generated based on the actual product purchased.

## Environment Setup

Add to your `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```

Get your free API key from: https://console.groq.com/

## Running

```bash
cd backend/agents/worker_agents/stylist
python app.py
```

Server: `http://localhost:8006`
