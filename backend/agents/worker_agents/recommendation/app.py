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
    mode: str = Field("normal", description="Recommendation mode: normal, gifting_genius, trendseer")
    intent: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="User intent: category, occasion, budget_min, budget_max, gender (male/female/unisex)"
    )
    current_cart_skus: List[str] = Field(
        default_factory=list,
        description="SKUs currently in cart for cross-sell suggestions"
    )
    limit: int = Field(5, ge=1, le=20, description="Number of recommendations to return")
    
    # Gifting Genius specific fields
    recipient_relation: Optional[str] = Field(None, description="Recipient relation (e.g., mother, friend)")
    recipient_gender: Optional[str] = Field(None, description="Recipient gender (overrides customer gender)")
    interests: Optional[List[str]] = Field(default_factory=list, description="Recipient interests")
    occasion: Optional[str] = Field(None, description="Gift occasion (birthday, anniversary, festive)")
    safe_sizes_only: bool = Field(False, description="Prefer size-free items like accessories")
    preferred_brands: Optional[List[str]] = Field(default_factory=list, description="Preferred brands")

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
    
    # Optional fields for gifting mode
    gift_message: Optional[str] = None
    gift_suitability: Optional[str] = None
    
    # Optional field for trendseer mode
    trend_capsule: Optional[bool] = None


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
        # Use word boundaries to prevent 'men' from matching in 'women'
        if target_gender == 'male':
            # For male: must contain men/man/boys/men's, must NOT contain women/woman/girls/women's
            filtered = filtered[
                (filtered['ProductDisplayName'].str.contains(r'\b(men|man|boys|men\'s)\b', case=False, na=False, regex=True)) &
                (~filtered['ProductDisplayName'].str.contains(r'\b(women|woman|girls|women\'s)\b', case=False, na=False, regex=True))
            ]
        else:  # female
            # For female: must contain women/woman/girls/women's, must NOT contain men/man/boys/men's
            filtered = filtered[
                (filtered['ProductDisplayName'].str.contains(r'\b(women|woman|girls|women\'s)\b', case=False, na=False, regex=True)) &
                (~filtered['ProductDisplayName'].str.contains(r'\b(men|man|boys|men\'s)\b', case=False, na=False, regex=True))
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
# 3-MODE RECOMMENDATION LOGIC
# ==========================================

async def _mode_normal(request: RecommendationRequest, customer_profile: Dict, past_skus: List[str]) -> List[Dict]:
    """MODE 1: Normal Recommendation - casual shopping, category browsing"""
    
    target_gender = request.intent.get('gender', '').lower() if request.intent.get('gender') else customer_profile.get('gender', '').lower()
    
    # Filter and rank
    filtered = filter_products_by_intent(request.intent, customer_profile)
    if filtered.empty:
        filtered = products_df[products_df['ratings'] >= 4.5].copy()
    
    ranked = rank_products(filtered, customer_profile, past_skus)
    
    # Build recommendations with unique LLM reasons
    recommendations = []
    for _, product in ranked.head(request.limit * 3).iterrows():
        if len(recommendations) >= request.limit:
            break
        
        if not get_inventory_availability(product['sku']):
            continue
        
        # Generate UNIQUE personalized reason via LLM
        reason = generate_personalized_reason(
            product, customer_profile, past_skus,
            context="recommendation",
            target_gender=target_gender
        )
        
        recommendations.append({
            'sku': product['sku'],
            'name': product['ProductDisplayName'],
            'brand': product['brand'],
            'category': product['category'],
            'subcategory': product['subcategory'],
            'price': float(product['price']),
            'rating': float(product['ratings']),
            'in_stock': True,
            'personalized_reason': reason
        })
    
    return recommendations


async def _mode_gifting_genius(request: RecommendationRequest, customer_profile: Dict, past_skus: List[str]) -> List[Dict]:
    """MODE 2: Gifting Genius - emotion + context driven gifting"""
    
    recipient_gender = (request.recipient_gender or request.intent.get('gender', '')).lower()
    relation = request.recipient_relation or 'someone special'
    occasion = request.occasion or request.intent.get('occasion', 'gift')
    interests = request.interests or []
    
    logger.info(f"   🎁 Gift recipient: {relation} ({recipient_gender})")
    
    # Filter by recipient gender (NOT buyer gender)
    filtered = products_df.copy()
    
    if recipient_gender in ['male', 'female']:
        # Define keywords for matching and exclusion with word boundaries
        if recipient_gender == 'male':
            # For male: must contain men/man/boys/men's, must NOT contain women/woman/girls/women's
            filtered = filtered[
                (filtered['ProductDisplayName'].str.contains(r'\b(men|man|boys|men\'s)\b', case=False, na=False, regex=True)) &
                (~filtered['ProductDisplayName'].str.contains(r'\b(women|woman|girls|women\'s)\b', case=False, na=False, regex=True))
            ]
        else:  # female
            # For female: must contain women/woman/girls/women's, must NOT contain men/man/boys/men's
            filtered = filtered[
                (filtered['ProductDisplayName'].str.contains(r'\b(women|woman|girls|women\'s)\b', case=False, na=False, regex=True)) &
                (~filtered['ProductDisplayName'].str.contains(r'\b(men|man|boys|men\'s)\b', case=False, na=False, regex=True))
            ]
        
        logger.info(f"   Filtered to {len(filtered)} gender-appropriate gift products")
    
    # Prefer size-free items
    if request.safe_sizes_only:
        size_free = filtered[filtered['category'].isin(['Accessories', 'Personal Care', 'Free Gifts'])]
        if not size_free.empty:
            filtered = size_free
    
    # Budget filter
    budget_min = request.intent.get('budget_min', 0)
    budget_max = request.intent.get('budget_max', 999999)
    filtered = filtered[(filtered['price'] >= budget_min) & (filtered['price'] <= budget_max)]
    
    # Brand filter
    if request.preferred_brands:
        brand_match = filtered[filtered['brand'].isin(request.preferred_brands)]
        if not brand_match.empty:
            filtered = brand_match
    
    # Interest matching
    if interests:
        scores = []
        for _, product in filtered.iterrows():
            score = sum(10 for interest in interests if interest.lower() in str(product['ProductDisplayName']).lower())
            scores.append(score)
        filtered['interest_score'] = scores
        filtered = filtered[filtered['interest_score'] > 0].sort_values('interest_score', ascending=False)
    
    if filtered.empty:
        filtered = products_df[(products_df['ratings'] >= 4.5) & 
                               (products_df['price'] >= budget_min) & 
                               (products_df['price'] <= budget_max)]
    
    filtered = filtered.sort_values('ratings', ascending=False)
    
    # Build gift recommendations with UNIQUE LLM reasons
    recommendations = []
    for _, product in filtered.head(request.limit * 2).iterrows():
        if len(recommendations) >= request.limit:
            break
        
        if not get_inventory_availability(product['sku']):
            continue
        
        # Generate TWO LLM responses: appropriateness reason + heartfelt message
        if llm_client:
            try:
                interests_text = ', '.join(interests) if interests else 'thoughtful gestures'
                
                # 1. Generate appropriateness reasoning (personalized_reason)
                reason_prompt = f"""You are a gift advisor. Explain in 1-2 sentences why this gift is appropriate for the recipient.

Gift Context:
- Recipient: Your {relation} ({recipient_gender})
- Interests: {interests_text}
- Occasion: {occasion}

Product:
- {product['ProductDisplayName']}
- {product['brand']} {product['subcategory']}
- ₹{product['price']}, {product['ratings']}⭐

Explain why this specific product is a fitting choice for this person and occasion. Focus on appropriateness, not emotion."""

                if LLM_PROVIDER == "gemini":
                    response = llm_client.generate_content(reason_prompt)
                    gift_reason = response.text.strip()
                elif LLM_PROVIDER == "groq":
                    response = llm_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": reason_prompt}],
                        temperature=0.7,
                        max_tokens=100
                    )
                    gift_reason = response.choices[0].message.content.strip()
                
                # 2. Generate heartfelt gift message (gift_message)
                message_prompt = f"""You are writing a heartfelt gift card message. Write a warm, personal message (1-2 sentences) for this gift.

Gift Context:
- Recipient: Your {relation}
- Occasion: {occasion}
- Product: {product['ProductDisplayName']} from {product['brand']}

Write a genuine, emotional message that the giver would write on a gift card. Be loving and heartfelt, not generic."""

                if LLM_PROVIDER == "gemini":
                    response = llm_client.generate_content(message_prompt)
                    gift_message = response.text.strip()
                elif LLM_PROVIDER == "groq":
                    response = llm_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": message_prompt}],
                        temperature=0.9,
                        max_tokens=80
                    )
                    gift_message = response.choices[0].message.content.strip()
                    
            except Exception as e:
                logger.warning(f"Gift LLM failed: {e}")
                gift_reason = f"This {product['subcategory']} is perfect for your {relation} — matches their style and the {occasion} occasion."
                gift_message = f"Happy {occasion.title()}! Hope you love this {product['brand']} gift!"
        else:
            gift_reason = f"A wonderful {occasion} gift for your {relation}."
            gift_message = f"Happy {occasion.title()}! Enjoy this special gift."
        
        # Suitability tag
        suitability = {'birthday': 'Birthday', 'anniversary': 'Anniversary', 'festive': 'Festive'}.get(occasion, 'General Gift')
        
        recommendations.append({
            'sku': product['sku'],
            'name': product['ProductDisplayName'],
            'brand': product['brand'],
            'category': product['category'],
            'subcategory': product['subcategory'],
            'price': float(product['price']),
            'rating': float(product['ratings']),
            'in_stock': True,
            'personalized_reason': gift_reason,
            'gift_message': gift_message,
            'gift_suitability': suitability
        })
    
    return recommendations


async def _mode_trendseer(request: RecommendationRequest, customer_profile: Dict, past_skus: List[str]) -> List[Dict]:
    """MODE 3: TrendSeer - predictive fashion oracle"""
    
    past_products = products_df[products_df['sku'].isin(past_skus)]
    
    if past_products.empty:
        logger.warning("   No purchase history for trendseer, using normal mode")
        return await _mode_normal(request, customer_profile, past_skus)
    
    # Get buyer's gender for personal purchases
    buyer_gender = customer_profile.get('gender', '').lower()
    logger.info(f"   🔮 Predicting for buyer gender: {buyer_gender}")
    
    # Build style profile
    fav_brands = past_products['brand'].value_counts().head(3).index.tolist()
    fav_categories = past_products['category'].value_counts().head(2).index.tolist()
    avg_spend = past_products['price'].mean()
    
    # Extract colors
    color_keywords = ['black', 'white', 'blue', 'red', 'navy', 'grey', 'pink', 'yellow', 'pastel']
    fav_colors = []
    for _, prod in past_products.iterrows():
        name_lower = str(prod['ProductDisplayName']).lower()
        for color in color_keywords:
            if color in name_lower:
                fav_colors.append(color)
    
    from collections import Counter
    if fav_colors:
        fav_colors = [c for c, _ in Counter(fav_colors).most_common(2)]
    
    # Detect trending SKUs
    recent_orders = orders_df.sort_values('order_date', ascending=False).head(200)
    trending_skus = recent_orders['product_sku'].value_counts().head(50).index.tolist()
    trending = products_df[products_df['sku'].isin(trending_skus)]
    
    # Filter by buyer's gender first (for their own purchases)
    if buyer_gender in ['male', 'female']:
        # Define keywords with word boundaries to prevent 'men' matching in 'women'
        if buyer_gender == 'male':
            # For male: must contain men/man/boys/men's, must NOT contain women/woman/girls/women's
            trending = trending[
                (trending['ProductDisplayName'].str.contains(r'\b(men|man|boys|men\'s)\b', case=False, na=False, regex=True)) &
                (~trending['ProductDisplayName'].str.contains(r'\b(women|woman|girls|women\'s)\b', case=False, na=False, regex=True))
            ]
        else:  # female
            # For female: must contain women/woman/girls/women's, must NOT contain men/man/boys/men's
            trending = trending[
                (trending['ProductDisplayName'].str.contains(r'\b(women|woman|girls|women\'s)\b', case=False, na=False, regex=True)) &
                (~trending['ProductDisplayName'].str.contains(r'\b(men|man|boys|men\'s)\b', case=False, na=False, regex=True))
            ]
        
        logger.info(f"   Filtered to {len(trending)} gender-appropriate trending products")
    
    # Match style
    filtered = trending[
        (trending['brand'].isin(fav_brands)) |
        (trending['category'].isin(fav_categories))
    ]
    
    filtered = filtered[
        (filtered['price'] >= avg_spend * 0.7) &
        (filtered['price'] <= avg_spend * 1.5)
    ]
    
    # Color matching
    if fav_colors:
        color_pattern = '|'.join(fav_colors)
        color_match = filtered[
            filtered['ProductDisplayName'].str.contains(color_pattern, case=False, na=False)
        ]
        if not color_match.empty:
            filtered = color_match
    
    # If no matches after filters, use ALL gender-filtered trending (not unfiltered)
    if filtered.empty:
        filtered = trending[trending['category'].isin(fav_categories)]
        if filtered.empty:
            # Last resort: use any gender-appropriate trending products
            filtered = trending
    
    filtered = filtered.sort_values('ratings', ascending=False)
    
    # Build UNIQUE predictive recommendations
    recommendations = []
    for _, product in filtered.head(request.limit * 2).iterrows():
        if len(recommendations) >= request.limit:
            break
        
        if not get_inventory_availability(product['sku']):
            continue
        
        # Generate UNIQUE predictive reason via LLM
        if llm_client:
            try:
                prompt = f"""You are a proactive personal stylist. Create a predictive recommendation (1-2 sentences).

Customer Style Profile:
- Favorite Brands: {', '.join(fav_brands[:2])}
- Favorite Categories: {', '.join(fav_categories)}
- Favorite Colors: {', '.join(fav_colors) if fav_colors else 'various'}
- Average Spend: ₹{avg_spend:.0f}

Trending Product:
- {product['ProductDisplayName']}
- {product['brand']} {product['subcategory']}
- ₹{product['price']}, {product['ratings']}⭐

Explain why they'll likely need this next based on their style. Be specific and predictive."""

                if LLM_PROVIDER == "gemini":
                    response = llm_client.generate_content(prompt)
                    predictive_reason = response.text.strip()
                elif LLM_PROVIDER == "groq":
                    response = llm_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.9,
                        max_tokens=120
                    )
                    predictive_reason = response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Trendseer LLM failed: {e}")
                predictive_reason = f"Trending now and matches your {fav_brands[0] if fav_brands else 'favorite'} style."
        else:
            predictive_reason = f"Trending this month, matches your preferences."
        
        recommendations.append({
            'sku': product['sku'],
            'name': product['ProductDisplayName'],
            'brand': product['brand'],
            'category': product['category'],
            'subcategory': product['subcategory'],
            'price': float(product['price']),
            'rating': float(product['ratings']),
            'in_stock': True,
            'personalized_reason': predictive_reason,
            'trend_capsule': True
        })
    
    return recommendations


# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Recommendation Agent",
        "version": "2.0.0 (3-Mode Intelligent Agent)",
        "products_loaded": len(products_df),
        "customers_loaded": len(customers_df)
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Generate personalized product recommendations with 3 modes:
    - normal: Regular shopping recommendations
    - gifting_genius: Emotion-driven gift recommendations
    - trendseer: Predictive fashion AI
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
    logger.info(f"   Mode: {request.mode}")
    
    # ==========================================
    # MODE ROUTING
    # ==========================================
    
    in_stock_products = []
    
    if request.mode == "gifting_genius":
        logger.info("   🎁 GIFTING GENIUS MODE activated")
        in_stock_products = await _mode_gifting_genius(request, customer_profile, past_skus)
        
    elif request.mode == "trendseer":
        logger.info("   🔮 TRENDSEER MODE activated")
        in_stock_products = await _mode_trendseer(request, customer_profile, past_skus)
        
    else:  # normal mode
        logger.info("   👤 NORMAL MODE activated")
        in_stock_products = await _mode_normal(request, customer_profile, past_skus)
    
    # Generate overall reasoning
    name = customer_profile.get('name', 'Customer').split()[0]
    loyalty_tier = customer_profile.get('loyalty_tier', 'Bronze')
    
    mode_descriptions = {
        'gifting_genius': f"I've found {len(in_stock_products)} perfect gift options",
        'trendseer': f"Here are {len(in_stock_products)} trending picks that match your style",
        'normal': f"I've curated {len(in_stock_products)} recommendations just for you"
    }
    
    reasoning = f"Hi {name}! As a {loyalty_tier} member, {mode_descriptions.get(request.mode, mode_descriptions['normal'])}!"
    
    logger.info(f"✅ Generated {len(in_stock_products)} recommendations")
    
    return RecommendationResponse(
        recommended_products=in_stock_products,
        upsell=None,  # Modes handle recommendations directly
        cross_sell=None,
        personalized_reasoning=reasoning,
        metadata={
            "customer_id": request.customer_id,
            "loyalty_tier": loyalty_tier,
            "mode": request.mode,
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