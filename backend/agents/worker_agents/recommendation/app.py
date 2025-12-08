# Recommendation Agent - FastAPI Server
# Endpoints: POST /recommend - Personalized product recommendations with AI-powered reasoning

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import pandas as pd
import json
import ast
from pathlib import Path
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# LLM imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini" or "groq"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm_client = None
gemini_model_name = None

if LLM_PROVIDER == "gemini" and GEMINI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # List available models and pick the best one
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Prefer flash models for speed
        if 'models/gemini-1.5-flash-latest' in available_models:
            gemini_model_name = 'models/gemini-1.5-flash-latest'
        elif 'models/gemini-1.5-flash' in available_models:
            gemini_model_name = 'models/gemini-1.5-flash'
        elif any('gemini-1.5' in m for m in available_models):
            gemini_model_name = [m for m in available_models if 'gemini-1.5' in m][0]
        elif any('gemini' in m for m in available_models):
            gemini_model_name = [m for m in available_models if 'gemini' in m][0]
        
        if gemini_model_name:
            llm_client = genai.GenerativeModel(gemini_model_name)
            logger.info(f"✅ Using Gemini ({gemini_model_name}) for personalized reasoning")
        else:
            logger.warning("⚠️  No compatible Gemini model found")
    except Exception as e:
        logger.warning(f"⚠️  Could not initialize Gemini: {e}")
        
elif LLM_PROVIDER == "groq" and GROQ_AVAILABLE and GROQ_API_KEY:
    llm_client = Groq(api_key=GROQ_API_KEY)
    logger.info("✅ Using Groq for personalized reasoning")
else:
    logger.warning("⚠️  No LLM configured - using template-based reasoning")
    logger.warning("   Set GEMINI_API_KEY or GROQ_API_KEY in .env for better personalization")

app = FastAPI(
    title="Recommendation Agent",
    description="Personalized product recommendations with intelligent reasoning",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# DATA LOADING
# ==========================================

# Load CSV data
DATA_PATH = Path(__file__).parent.parent.parent.parent / "data"

try:
    products_df = pd.read_csv(DATA_PATH / "products.csv")
    customers_df = pd.read_csv(DATA_PATH / "customers.csv")
    orders_df = pd.read_csv(DATA_PATH / "orders.csv")
    inventory_df = pd.read_csv(DATA_PATH / "inventory.csv")
    
    logger.info(f"✅ Loaded {len(products_df)} products")
    logger.info(f"✅ Loaded {len(customers_df)} customers")
    logger.info(f"✅ Loaded {len(orders_df)} orders")
    logger.info(f"✅ Loaded {len(inventory_df)} inventory records")
except Exception as e:
    logger.error(f"❌ Failed to load data: {e}")
    products_df = pd.DataFrame()
    customers_df = pd.DataFrame()
    orders_df = pd.DataFrame()
    inventory_df = pd.DataFrame()

# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class RecommendationRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID for personalization")
    intent: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="User intent: category, occasion, budget_min, budget_max, gender (male/female/unisex)"
    )
    current_cart_skus: List[str] = Field(
        default_factory=list,
        description="SKUs currently in cart for cross-sell suggestions"
    )
    limit: int = Field(5, ge=1, le=20, description="Number of recommendations to return")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "customer_id": "104",
                "intent": {
                    "category": "Footwear",
                    "occasion": "casual",
                    "gender": "female",
                    "budget_min": 1000,
                    "budget_max": 5000
                },
                "current_cart_skus": ["SKU000001"],
                "limit": 5
            }]
        }
    }


class Product(BaseModel):
    sku: str
    name: str
    brand: str
    category: str
    subcategory: str
    price: float
    rating: float
    in_stock: bool
    personalized_reason: str


class RecommendationResponse(BaseModel):
    recommended_products: List[Product]
    upsell: Optional[Product] = None
    cross_sell: Optional[Product] = None
    personalized_reasoning: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# RECOMMENDATION ENGINE
# ==========================================

def get_customer_profile(customer_id: str) -> Optional[Dict]:
    """Get customer profile from customers.csv"""
    customer = customers_df[customers_df['customer_id'] == int(customer_id)]
    
    if customer.empty:
        logger.warning(f"Customer {customer_id} not found")
        return None
    
    customer_data = customer.iloc[0].to_dict()
    
    # Parse purchase history
    try:
        purchase_history = ast.literal_eval(customer_data['purchase_history'])
        customer_data['purchase_history'] = purchase_history
    except:
        customer_data['purchase_history'] = []
    
    return customer_data


def get_past_purchase_skus(customer_profile: Dict) -> List[str]:
    """Extract SKUs from purchase history"""
    skus = []
    purchase_history = customer_profile.get('purchase_history', [])
    
    for purchase in purchase_history:
        if isinstance(purchase, dict) and 'sku' in purchase:
            skus.append(purchase['sku'])
    
    return skus


def get_inventory_availability(sku: str) -> bool:
    """Check if product is in stock (online or any store)"""
    inventory = inventory_df[inventory_df['sku'] == sku]
    
    if inventory.empty:
        return False
    
    # Check if any location has stock > 0
    total_stock = inventory['qty'].sum()
    return total_stock > 0


def filter_products_by_intent(
    intent: Dict[str, Any],
    customer_profile: Dict
) -> pd.DataFrame:
    """Filter products based on user intent and customer profile"""
    
    filtered = products_df.copy()
    
    # Filter by gender - prioritize intent gender over customer gender
    target_gender = intent.get('gender', '').lower() if intent.get('gender') else customer_profile.get('gender', '').lower()
    
    if target_gender in ['male', 'female']:
        # Check if products_df has a direct 'gender' column
        if 'gender' in filtered.columns:
            filtered = filtered[
                filtered['gender'].str.lower().isin([target_gender, 'unisex', 'boys', 'girls']) |
                filtered['gender'].isna()
            ]
            # Also filter by gender in product name if no gender column match
            if filtered.empty:
                gender_keywords = {
                    'male': ['men', 'man', 'male', 'boys'],
                    'female': ['women', 'woman', 'female', 'girls']
                }
                keywords = gender_keywords.get(target_gender, [])
                pattern = '|'.join(keywords)
                filtered = products_df[
                    products_df['ProductDisplayName'].str.contains(pattern, case=False, na=False)
                ]
        else:
            # Fallback: filter by product name keywords
            gender_keywords = {
                'male': ['men', 'man', 'male', 'boys'],
                'female': ['women', 'woman', 'female', 'girls']
            }
            keywords = gender_keywords.get(target_gender, [])
            pattern = '|'.join(keywords)
            filtered = filtered[
                filtered['ProductDisplayName'].str.contains(pattern, case=False, na=False)
            ]
    
    # Filter by category
    if 'category' in intent and intent['category']:
        category = intent['category']
        filtered = filtered[
            filtered['category'].str.contains(category, case=False, na=False) |
            filtered['subcategory'].str.contains(category, case=False, na=False)
        ]
    
    # Filter by price range
    if 'budget_min' in intent and intent['budget_min']:
        filtered = filtered[filtered['price'] >= intent['budget_min']]
    
    if 'budget_max' in intent and intent['budget_max']:
        filtered = filtered[filtered['price'] <= intent['budget_max']]
    
    return filtered


def rank_products(
    products: pd.DataFrame,
    customer_profile: Dict,
    past_skus: List[str]
) -> pd.DataFrame:
    """Rank products using rating, past purchases, and loyalty tier"""
    
    if products.empty:
        return products
    
    ranked = products.copy()
    
    # Base score from ratings
    ranked['score'] = ranked['ratings'] * 10
    
    # Boost from past brand purchases
    past_brands = []
    if past_skus:
        past_products = products_df[products_df['sku'].isin(past_skus)]
        past_brands = past_products['brand'].unique().tolist()
    
    if past_brands:
        ranked['score'] += ranked['brand'].apply(
            lambda x: 15 if x in past_brands else 0
        )
    
    # Loyalty tier boost
    loyalty_tier = customer_profile.get('loyalty_tier', 'Bronze')
    tier_boost = {'Gold': 10, 'Silver': 5, 'Bronze': 0}
    ranked['score'] += tier_boost.get(loyalty_tier, 0)
    
    # Sort by score
    ranked = ranked.sort_values('score', ascending=False)
    
    return ranked


def generate_personalized_reason(
    product: pd.Series,
    customer_profile: Dict,
    past_skus: List[str],
    context: str = "recommendation",
    target_gender: str = None
) -> str:
    """Generate human-like personalized reasoning for recommendation using LLM"""
    
    name = customer_profile.get('name', 'Customer')
    first_name = name.split()[0]
    customer_gender = customer_profile.get('gender', '')
    loyalty_tier = customer_profile.get('loyalty_tier', 'Bronze')
    age = customer_profile.get('age', 'N/A')
    total_spend = customer_profile.get('total_spend', 0)
    
    brand = product['brand']
    category = product['subcategory']
    price = product['price']
    rating = product['ratings']
    product_name = product['ProductDisplayName']
    
    # Check if this is gift-giving scenario
    is_gift = target_gender and target_gender.lower() != customer_gender.lower()
    
    # Get past brands
    past_brands = []
    past_categories = []
    if past_skus:
        past_products = products_df[products_df['sku'].isin(past_skus)]
        past_brands = past_products['brand'].unique().tolist()
        past_categories = past_products['subcategory'].unique().tolist()
    
    # Use LLM if available
    if llm_client:
        try:
            gift_context = ""
            if is_gift:
                gift_context = f"\n\nIMPORTANT: {first_name} (a {customer_gender}) is shopping for {target_gender} products - this is likely a gift! Mention this thoughtfully in your recommendation."
            
            prompt = f"""You are a friendly, knowledgeable shopping assistant. Generate a brief, natural, personalized recommendation reason (1-2 sentences max).

Customer Profile:
- Name: {first_name}
- Age: {age}
- Gender: {customer_gender}
- Loyalty Tier: {loyalty_tier}
- Total Spend: ₹{total_spend}
- Previously Bought Brands: {', '.join(past_brands[:3]) if past_brands else 'None'}
- Previously Bought Categories: {', '.join(past_categories[:3]) if past_categories else 'None'}

Product to Recommend:
- Name: {product_name}
- Brand: {brand}
- Category: {category}
- Price: ₹{price}
- Rating: {rating}★
- Target Gender: {target_gender or customer_gender}
{gift_context}

Context: This is {"an upsell suggestion" if context == "upsell" else "a cross-sell item" if context == "cross_sell" else "a main recommendation"}

Write a warm, personalized reason (1-2 sentences) explaining why {first_name} would love this product{" as a gift" if is_gift else ""}. Be specific, mention their history or preferences, and sound like a helpful friend - not a salesperson. Keep it conversational and genuine."""

            if LLM_PROVIDER == "gemini":
                response = llm_client.generate_content(prompt)
                return response.text.strip()
            
            elif LLM_PROVIDER == "groq":
                response = llm_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}, falling back to template")
    
    # Fallback to template-based reasoning
    reasons = []
    
    # Gift context
    if is_gift:
        reasons.append(f"this makes a perfect gift for the {target_gender} in your life")
    
    # Brand loyalty
    if brand in past_brands:
        reasons.append(f"you've loved {brand} products before")
    
    # Loyalty tier
    if loyalty_tier == 'Gold':
        reasons.append(f"this premium {category} matches your Gold member status")
    elif loyalty_tier == 'Silver':
        reasons.append(f"as a Silver member, you'll appreciate this quality {category}")
    
    # High rating
    if rating >= 4.5:
        reasons.append(f"it has an excellent {rating}⭐ rating from customers")
    
    # Context-specific
    if context == "upsell":
        reasons.append(f"it's a premium upgrade that complements perfectly")
    elif context == "cross_sell":
        reasons.append(f"customers often pair this {category} with similar items")
    
    # Construct final message
    if reasons:
        reason_text = ", and ".join(reasons[:2])
        return f"Since {reason_text}, I'm confident this {product_name} is a great choice."
    else:
        return f"This {product_name} is a {rating}⭐ rated {category} from {brand} that's perfect for {target_gender or 'you'}."


def get_upsell_product(
    base_products: pd.DataFrame,
    customer_profile: Dict,
    past_skus: List[str],
    current_price_range: tuple
) -> Optional[Dict]:
    """Find premium upsell opportunity"""
    
    min_price, max_price = current_price_range
    upsell_min = max_price * 1.2  # 20% more expensive
    upsell_max = max_price * 1.8  # Up to 80% more expensive
    
    upsells = base_products[
        (base_products['price'] >= upsell_min) &
        (base_products['price'] <= upsell_max) &
        (base_products['ratings'] >= 4.3)
    ]
    
    if upsells.empty:
        return None
    
    # Pick top rated
    upsell = upsells.sort_values('ratings', ascending=False).iloc[0]
    
    return {
        'sku': upsell['sku'],
        'name': upsell['ProductDisplayName'],
        'brand': upsell['brand'],
        'category': upsell['category'],
        'subcategory': upsell['subcategory'],
        'price': float(upsell['price']),
        'rating': float(upsell['ratings']),
        'in_stock': get_inventory_availability(upsell['sku']),
        'personalized_reason': generate_personalized_reason(
            upsell, customer_profile, past_skus, context="upsell"
        )
    }


def get_cross_sell_product(
    cart_skus: List[str],
    customer_profile: Dict,
    past_skus: List[str]
) -> Optional[Dict]:
    """Find complementary cross-sell item"""
    
    if not cart_skus:
        return None
    
    # Get categories of items in cart
    cart_products = products_df[products_df['sku'].isin(cart_skus)]
    
    if cart_products.empty:
        return None
    
    cart_categories = cart_products['category'].unique()
    
    # Cross-sell mapping
    cross_sell_map = {
        'Footwear': ['Apparel', 'Accessories'],
        'Apparel': ['Footwear', 'Accessories'],
        'Accessories': ['Apparel', 'Footwear'],
        'Personal Care': ['Accessories']
    }
    
    # Find complementary categories
    target_categories = []
    for cat in cart_categories:
        target_categories.extend(cross_sell_map.get(cat, []))
    
    if not target_categories:
        return None
    
    # Filter products
    cross_sells = products_df[
        products_df['category'].isin(target_categories) &
        (products_df['ratings'] >= 4.0)
    ]
    
    if cross_sells.empty:
        return None
    
    # Rank and pick top
    ranked = rank_products(cross_sells, customer_profile, past_skus)
    cross_sell = ranked.iloc[0]
    
    return {
        'sku': cross_sell['sku'],
        'name': cross_sell['ProductDisplayName'],
        'brand': cross_sell['brand'],
        'category': cross_sell['category'],
        'subcategory': cross_sell['subcategory'],
        'price': float(cross_sell['price']),
        'rating': float(cross_sell['ratings']),
        'in_stock': get_inventory_availability(cross_sell['sku']),
        'personalized_reason': generate_personalized_reason(
            cross_sell, customer_profile, past_skus, context="cross_sell"
        )
    }


# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Recommendation Agent",
        "version": "1.0.0",
        "products_loaded": len(products_df),
        "customers_loaded": len(customers_df)
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Generate personalized product recommendations
    
    This endpoint uses customer profile, purchase history, and intent
    to provide intelligent, personalized recommendations with human-like reasoning.
    """
    
    logger.info(f"📊 Processing recommendation request for customer: {request.customer_id}")
    
    # Get customer profile
    customer_profile = get_customer_profile(request.customer_id)
    
    if not customer_profile:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {request.customer_id} not found"
        )
    
    # Get past purchases
    past_skus = get_past_purchase_skus(customer_profile)
    logger.info(f"   Past purchases: {len(past_skus)} items")
    
    # Determine target gender (from intent or customer profile)
    target_gender = request.intent.get('gender', customer_profile.get('gender', ''))
    is_gift = request.intent.get('gender') and request.intent.get('gender').lower() != customer_profile.get('gender', '').lower()
    
    if is_gift:
        logger.info(f"   🎁 Gift mode: Customer is {customer_profile.get('gender', 'N/A')}, looking for {target_gender} products")
    
    # Filter products by intent
    filtered_products = filter_products_by_intent(request.intent, customer_profile)
    logger.info(f"   Filtered to: {len(filtered_products)} products")
    
    # Handle empty results - fallback to trending
    if filtered_products.empty:
        logger.warning("   No products match filters, using trending items")
        filtered_products = products_df[products_df['ratings'] >= 4.5].copy()
    
    # Rank products
    ranked_products = rank_products(filtered_products, customer_profile, past_skus)
    
    # Check inventory and filter in-stock items
    top_products = ranked_products.head(request.limit * 3)  # Get extra for filtering
    in_stock_products = []
    
    for _, product in top_products.iterrows():
        if len(in_stock_products) >= request.limit:
            break
        
        is_available = get_inventory_availability(product['sku'])
        
        if is_available or len(in_stock_products) < request.limit // 2:
            in_stock_products.append({
                'sku': product['sku'],
                'name': product['ProductDisplayName'],
                'brand': product['brand'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'price': float(product['price']),
                'rating': float(product['ratings']),
                'in_stock': is_available,
                'personalized_reason': generate_personalized_reason(
                    product, customer_profile, past_skus,
                    context="recommendation",
                    target_gender=target_gender
                )
            })
    
    # Get price range for recommendations
    if in_stock_products:
        prices = [p['price'] for p in in_stock_products]
        price_range = (min(prices), max(prices))
    else:
        price_range = (0, 10000)
    
    # Generate upsell
    upsell = get_upsell_product(
        ranked_products,
        customer_profile,
        past_skus,
        price_range
    )
    
    # Generate cross-sell
    cross_sell = get_cross_sell_product(
        request.current_cart_skus,
        customer_profile,
        past_skus
    )
    
    # Generate overall reasoning with LLM
    name = customer_profile.get('name', 'Customer').split()[0]
    loyalty_tier = customer_profile.get('loyalty_tier', 'Bronze')
    age = customer_profile.get('age', 'N/A')
    
    if llm_client:
        try:
            # Get product names for context
            product_names = [p['name'] for p in in_stock_products[:3]]
            
            prompt = f"""You are a warm, friendly shopping assistant. Write a brief, personalized greeting and introduction (2-3 sentences max) for recommendations.

Customer: {name}, Age {age}, {loyalty_tier} tier member
Has {len(past_skus)} past purchases
Recommending {len(in_stock_products)} products: {', '.join(product_names)}
{f"For {request.intent.get('occasion')} occasion" if request.intent.get('occasion') else ""}

Write a warm, conversational introduction that:
1. Greets {name} personally
2. Mentions their loyalty tier naturally
3. Hints at why these picks are special for them
4. Sounds like a helpful friend, not a salesperson

Keep it brief, warm, and genuine."""

            if LLM_PROVIDER == "gemini":
                response = llm_client.generate_content(prompt)
                reasoning = response.text.strip()
            elif LLM_PROVIDER == "groq":
                response = llm_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=200
                )
                reasoning = response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.warning(f"LLM generation failed for overall reasoning: {e}")
            reasoning = f"Hi {name}! As a {loyalty_tier} member, I've curated these {len(in_stock_products)} picks just for you!"
    else:
        # Fallback template
        reasoning = f"Hi {name}! As a {loyalty_tier} member with a taste for quality, "
        
        if past_skus:
            reasoning += f"I've curated these {len(in_stock_products)} recommendations based on your past purchases and preferences. "
        else:
            reasoning += f"I've selected these {len(in_stock_products)} trending items that match your style profile. "
        
        if request.intent.get('occasion'):
            reasoning += f"They're perfect for {request.intent['occasion']} occasions. "
        
        reasoning += "Each pick is specially chosen with you in mind!"
    
    logger.info(f"✅ Generated {len(in_stock_products)} recommendations")
    
    return RecommendationResponse(
        recommended_products=in_stock_products,
        upsell=upsell,
        cross_sell=cross_sell,
        personalized_reasoning=reasoning,
        metadata={
            "customer_id": request.customer_id,
            "loyalty_tier": loyalty_tier,
            "past_purchases_count": len(past_skus),
            "intent": request.intent,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )
