"""
Virtual Style Circles Agent - FastAPI Microservice
Port: 8005
Integrates with EY CodeCrafters multi-agent system
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from contextlib import asynccontextmanager
import pandas as pd
import json
import math
import os
from pathlib import Path
import google.generativeai as genai

# In-memory storage (defined before app initialization)
customers_df = None
products_df = None
orders_df = None
user_profiles = {}
circles = {}  # circle_id -> [user_ids]
user_to_circle = {}  # user_id -> circle_id
circle_trends = {}  # circle_id -> trend data
interaction_log = []  # simulated interaction events

# Chat storage
circle_chats = {}  # circle_id -> [messages]
user_aliases = {}  # (user_id, circle_id) -> alias
user_message_timestamps = {}  # user_id -> [timestamps]
ai_insight_timers = {}  # circle_id -> last_insight_time


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - replaces deprecated on_event"""
    # Startup
    await load_data()
    yield
    # Shutdown (if needed)
    pass


app = FastAPI(title="Virtual Style Circles Agent", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SIMILARITY_THRESHOLD = 0.35
MAX_CIRCLE_SIZE = 50
INTERACTION_WEIGHTS = {
    "purchase": 10,
    "cart": 5,
    "like": 2,
    "view": 1
}

# Chat Configuration
MAX_MESSAGES_PER_CIRCLE = 100
MAX_MESSAGES_PER_MINUTE = 5
MIN_MESSAGE_LENGTH = 1
MAX_MESSAGE_LENGTH = 500
AI_INSIGHT_COOLDOWN_MINUTES = 15  # AI posts insights every 15 min max
CHAT_MENTION_WEIGHT = 3  # Weight for trend scoring

# Basic profanity filter (extend as needed)
PROFANITY_LIST = {
    "spam", "scam", "fake", "stupid", "idiot", "hate",
    # Add more as needed, kept minimal for demo
}

# Soft Taxonomy: Brand Groups
BRAND_GROUPS = {
    "sportswear": {"Nike", "Adidas", "Puma", "Reebok", "ADIDAS", "NIKE", "PUMA"},
    "formal": {"Van Heusen", "Allen Solly", "Louis Philippe", "Peter England", "Arrow"},
    "casual": {"Roadster", "HRX", "Levis", "United Colors of Benetton", "Wrangler", "Lee"},
    "ethnic": {"Fabindia", "Biba", "W", "Aurelia", "Global Desi"},
    "premium": {"Tommy Hilfiger", "Calvin Klein", "Hugo Boss", "Polo", "Lacoste"},
    "budget": {"Wildcraft", "Flying Machine", "SPYKAR", "Newport", "Basics"}
}

# Soft Taxonomy: Category Groups  
CATEGORY_GROUPS = {
    "footwear": {"Shoes", "Casual Shoes", "Sports Shoes", "Formal Shoes", "Sandals", "Flip Flops", "Heels"},
    "topwear": {"Shirts", "T-Shirts", "Tops", "Tshirts", "Sweaters", "Sweatshirts", "Jackets"},
    "bottomwear": {"Jeans", "Trousers", "Shorts", "Track Pants", "Leggings", "Capris"},
    "accessories": {"Watches", "Sunglasses", "Bags", "Belts", "Wallets", "Ties"},
    "innerwear": {"Innerwear", "Socks", "Briefs", "Trunks"},
    "activewear": {"Sports", "Track Suits", "Swimwear", "Sports Sandals"}
}

# Soft Taxonomy: Color Groups
COLOR_GROUPS = {
    "dark": {"black", "navy", "brown", "grey", "gray"},
    "light": {"white", "beige", "khaki", "cream"},
    "bright": {"red", "blue", "green", "yellow", "pink", "purple", "orange", "olive"}
}

# Fallback Circles for Cold-Start Users
FALLBACK_CIRCLES = {
    "casual_explorers": {
        "name": "Casual Explorers",
        "description": "Users exploring casual fashion",
        "criteria": lambda p: "casual" in [get_brand_group(b) for b in p.get('top_brands', [])] or 
                              "topwear" in [get_category_group(c) for c in p.get('top_categories', [])]
    },
    "value_seekers": {
        "name": "Value Seekers",
        "description": "Budget-conscious shoppers",
        "criteria": lambda p: p.get('avg_price', 0) < 1500
    },
    "sports_lovers": {
        "name": "Sportswear Lovers",
        "description": "Active lifestyle enthusiasts",
        "criteria": lambda p: "sportswear" in [get_brand_group(b) for b in p.get('top_brands', [])] or
                              "activewear" in [get_category_group(c) for c in p.get('top_categories', [])]
    },
    "premium_shoppers": {
        "name": "Premium Shoppers",
        "description": "High-value customers",
        "criteria": lambda p: p.get('avg_price', 0) > 3000
    },
    "new_arrivals": {
        "name": "New Arrivals",
        "description": "New customers still finding their style",
        "criteria": lambda p: True  # Default fallback
    }
}

# Pydantic Models
class InteractionEvent(BaseModel):
    user_id: str
    sku: str
    event_type: str  # view, like, cart, purchase
    timestamp: Optional[str] = None

class StyleProfile(BaseModel):
    user_id: str
    top_brands: List[str]
    top_categories: List[str]
    preferred_colors: List[str]
    avg_price: float
    price_range: tuple

class CircleInfo(BaseModel):
    circle_id: str
    user_count: int
    avg_order_value: float
    top_brands: List[str]
    top_categories: List[str]

class TrendItem(BaseModel):
    sku: str
    product_name: str
    brand: str
    score: float
    trend_label: str  # Rising, Peaking, Emerging
    interaction_count: int
    velocity: float

class Recommendation(BaseModel):
    sku: str
    product_name: str
    brand: str
    price: float
    image_url: str
    score: float
    explanation: str

class ChatMessage(BaseModel):
    user_id: str
    text: str

class ChatMessageResponse(BaseModel):
    message_id: str
    circle_id: str
    alias: str
    text: str
    timestamp: str
    type: str  # "user" or "ai_insight"


# ==================== DATA LOADING ====================

async def load_data():
    """Load CSV data on startup"""
    global customers_df, products_df, orders_df
    
    # Path from: backend/agents/worker_agents/virtual_circles/app.py
    # To: backend/data/
    data_path = Path(__file__).parent.parent.parent.parent / "data"
    
    print(f"📁 Looking for data at: {data_path.absolute()}")
    
    try:
        customers_df = pd.read_csv(data_path / "customers.csv")
        products_df = pd.read_csv(data_path / "products.csv")
        orders_df = pd.read_csv(data_path / "orders.csv")
        
        print(f"✅ Loaded {len(customers_df)} customers")
        print(f"✅ Loaded {len(products_df)} products")
        print(f"✅ Loaded {len(orders_df)} orders")
        
        # Parse orders to extract SKUs from JSON items
        _parse_order_items()
        
        # Initialize style profiles and circles
        _initialize_profiles()
        _form_circles()
        _simulate_interactions()
        
    except Exception as e:
        import traceback
        print(f"❌ Error loading data: {e}")
        traceback.print_exc()


def _parse_order_items():
    """Parse JSON items column to extract SKU information"""
    global orders_df
    
    expanded_orders = []
    
    for _, row in orders_df.iterrows():
        try:
            items = json.loads(row['items'])
            for item in items:
                expanded_orders.append({
                    'order_id': row['order_id'],
                    'customer_id': str(row['customer_id']),
                    'sku': item['sku'],
                    'qty': item['qty'],
                    'unit_price': item['unit_price'],
                    'line_total': item['line_total'],
                    'created_at': row['created_at']
                })
        except:
            continue
    
    # Replace orders_df with expanded version
    orders_df = pd.DataFrame(expanded_orders)
    print(f"✅ Expanded to {len(orders_df)} order line items")


def _initialize_profiles():
    """Create style profiles for all users"""
    global user_profiles
    
    for customer_id in orders_df['customer_id'].unique():
        profile = _build_style_profile(str(customer_id))
        if profile:
            user_profiles[str(customer_id)] = profile
    
    print(f"✅ Created {len(user_profiles)} style profiles")


def _build_style_profile(user_id: str) -> Optional[Dict]:
    """Build style profile from order history"""
    user_orders = orders_df[orders_df['customer_id'] == user_id]
    
    if len(user_orders) == 0:
        return None
    
    # Get product details
    skus = user_orders['sku'].tolist()
    user_products = products_df[products_df['sku'].isin(skus)]
    
    if len(user_products) == 0:
        return None
    
    # Extract attributes
    brands = user_products['brand'].value_counts().head(3).index.tolist()
    categories = user_products['category'].value_counts().head(3).index.tolist()
    
    # Extract colors from product names
    colors = _extract_colors(user_products['ProductDisplayName'].tolist())
    
    # Price analysis
    prices = user_products['price'].dropna()
    avg_price = prices.mean() if len(prices) > 0 else 0
    price_range = (prices.min(), prices.max()) if len(prices) > 0 else (0, 0)
    
    return {
        "user_id": user_id,
        "top_brands": brands,
        "top_categories": categories,
        "preferred_colors": colors[:3],
        "avg_price": float(avg_price),
        "price_range": (float(price_range[0]), float(price_range[1]))
    }


def _extract_colors(product_names: List[str]) -> List[str]:
    """Extract color mentions from product names"""
    color_keywords = [
        "black", "white", "blue", "red", "green", "yellow", "pink", "purple",
        "orange", "brown", "gray", "grey", "navy", "beige", "khaki", "olive"
    ]
    
    color_counts = Counter()
    for name in product_names:
        name_lower = name.lower()
        for color in color_keywords:
            if color in name_lower:
                color_counts[color] += 1
    
    return [color for color, _ in color_counts.most_common(5)]


# ==================== TAXONOMY HELPER FUNCTIONS ====================

def get_brand_group(brand: str) -> Optional[str]:
    """Get the group a brand belongs to"""
    if not brand:
        return None
    for group_name, brands in BRAND_GROUPS.items():
        if brand in brands:
            return group_name
    return "other"


def get_category_group(category: str) -> Optional[str]:
    """Get the group a category belongs to"""
    if not category:
        return None
    for group_name, categories in CATEGORY_GROUPS.items():
        if category in categories:
            return group_name
    return "other"


def get_color_group(color: str) -> Optional[str]:
    """Get the group a color belongs to"""
    if not color:
        return None
    for group_name, colors in COLOR_GROUPS.items():
        if color in colors:
            return group_name
    return "neutral"


# ==================== SIMILARITY & CIRCLES ====================

def _calculate_similarity(profile1: Dict, profile2: Dict) -> float:
    """Calculate similarity between two user profiles using soft scoring"""
    score = 0.0
    
    # Brand similarity with soft matching (40%)
    brands1 = profile1['top_brands']
    brands2 = profile2['top_brands']
    if brands1 and brands2:
        brand_score = _calculate_soft_brand_similarity(brands1, brands2)
        score += brand_score * 0.4
    
    # Category similarity with soft matching (30%)
    cats1 = profile1['top_categories']
    cats2 = profile2['top_categories']
    if cats1 and cats2:
        cat_score = _calculate_soft_category_similarity(cats1, cats2)
        score += cat_score * 0.3
    
    # Price range proximity (20%) - unchanged
    avg1 = profile1['avg_price']
    avg2 = profile2['avg_price']
    if avg1 > 0 and avg2 > 0:
        price_diff = abs(avg1 - avg2) / max(avg1, avg2)
        price_score = max(0, 1 - price_diff)
        score += price_score * 0.2
    
    # Color similarity with soft matching (10%)
    colors1 = profile1['preferred_colors']
    colors2 = profile2['preferred_colors']
    if colors1 and colors2:
        color_score = _calculate_soft_color_similarity(colors1, colors2)
        score += color_score * 0.1
    
    return score


def _calculate_soft_brand_similarity(brands1: List[str], brands2: List[str]) -> float:
    """Calculate soft brand similarity: exact match = 1.0, same group = 0.6, no match = 0"""
    if not brands1 or not brands2:
        return 0.0
    
    exact_matches = 0
    group_matches = 0
    
    brands1_set = set(brands1)
    brands2_set = set(brands2)
    
    # Count exact matches
    exact_matches = len(brands1_set & brands2_set)
    
    # Count group matches (excluding exact matches)
    brands1_groups = {get_brand_group(b) for b in brands1_set}
    brands2_groups = {get_brand_group(b) for b in brands2_set}
    
    for b1 in brands1_set:
        if b1 in brands2_set:
            continue  # Already counted as exact
        group1 = get_brand_group(b1)
        for b2 in brands2_set:
            if b2 in brands1_set:
                continue
            group2 = get_brand_group(b2)
            if group1 and group2 and group1 == group2 and group1 != "other":
                group_matches += 0.5  # Partial credit, averaged across pairs
                break
    
    total_brands = max(len(brands1_set), len(brands2_set))
    weighted_score = (exact_matches * 1.0 + group_matches * 0.6) / total_brands
    
    return min(weighted_score, 1.0)


def _calculate_soft_category_similarity(cats1: List[str], cats2: List[str]) -> float:
    """Calculate soft category similarity: exact match = 1.0, same group = 0.6, no match = 0"""
    if not cats1 or not cats2:
        return 0.0
    
    exact_matches = 0
    group_matches = 0
    
    cats1_set = set(cats1)
    cats2_set = set(cats2)
    
    # Count exact matches
    exact_matches = len(cats1_set & cats2_set)
    
    # Count group matches (excluding exact matches)
    for c1 in cats1_set:
        if c1 in cats2_set:
            continue  # Already counted as exact
        group1 = get_category_group(c1)
        for c2 in cats2_set:
            if c2 in cats1_set:
                continue
            group2 = get_category_group(c2)
            if group1 and group2 and group1 == group2 and group1 != "other":
                group_matches += 0.5  # Partial credit
                break
    
    total_cats = max(len(cats1_set), len(cats2_set))
    weighted_score = (exact_matches * 1.0 + group_matches * 0.6) / total_cats
    
    return min(weighted_score, 1.0)


def _calculate_soft_color_similarity(colors1: List[str], colors2: List[str]) -> float:
    """Calculate soft color similarity: exact match = 1.0, same group = 0.6, no match = 0"""
    if not colors1 or not colors2:
        return 0.0
    
    exact_matches = 0
    group_matches = 0
    
    colors1_set = set(colors1)
    colors2_set = set(colors2)
    
    # Count exact matches
    exact_matches = len(colors1_set & colors2_set)
    
    # Count group matches (excluding exact matches)
    for col1 in colors1_set:
        if col1 in colors2_set:
            continue  # Already counted as exact
        group1 = get_color_group(col1)
        for col2 in colors2_set:
            if col2 in colors1_set:
                continue
            group2 = get_color_group(col2)
            if group1 and group2 and group1 == group2 and group1 != "neutral":
                group_matches += 0.5  # Partial credit
                break
    
    total_colors = max(len(colors1_set), len(colors2_set))
    weighted_score = (exact_matches * 1.0 + group_matches * 0.6) / total_colors
    
    return min(weighted_score, 1.0)


def _is_low_signal_user(user_id: str) -> bool:
    """Detect if user has insufficient signal for clustering"""
    user_orders = orders_df[orders_df['customer_id'] == user_id]
    return len(user_orders) < 2


def _assign_to_fallback_circle(user_id: str, user_profile: Dict) -> str:
    """Assign low-signal user to best matching fallback circle"""
    # Try each fallback circle's criteria
    for fallback_id, fallback_info in FALLBACK_CIRCLES.items():
        try:
            if fallback_info['criteria'](user_profile):
                print(f"   🔄 Assigned {user_id} to fallback: {fallback_info['name']}")
                return f"fallback_{fallback_id}"
        except:
            continue
    
    # Default to new_arrivals
    print(f"   🔄 Assigned {user_id} to fallback: New Arrivals (default)")
    return "fallback_new_arrivals"


def _form_circles():
    """Form style circles based on user similarity with fallback support"""
    global circles, user_to_circle
    
    circle_counter = 0
    assigned = set()
    low_signal_users = []
    
    # Initialize fallback circles
    for fallback_id in FALLBACK_CIRCLES.keys():
        circles[f"fallback_{fallback_id}"] = []
    
    user_ids = list(user_profiles.keys())
    
    # First pass: cluster high-signal users
    print("\n🔍 Phase 1: Clustering high-signal users...")
    for user_id in user_ids:
        if user_id in assigned:
            continue
        
        # Check if low-signal user
        if _is_low_signal_user(user_id):
            low_signal_users.append(user_id)
            continue
        
        # Create new circle
        circle_id = f"circle_{circle_counter}"
        circle_members = [user_id]
        assigned.add(user_id)
        
        # Find similar users
        user_profile = user_profiles[user_id]
        
        for other_id in user_ids:
            if other_id in assigned or len(circle_members) >= MAX_CIRCLE_SIZE:
                break
            
            if _is_low_signal_user(other_id):
                continue  # Skip low-signal users in primary clustering
            
            other_profile = user_profiles[other_id]
            similarity = _calculate_similarity(user_profile, other_profile)
            
            if similarity >= SIMILARITY_THRESHOLD:
                circle_members.append(other_id)
                assigned.add(other_id)
        
        circles[circle_id] = circle_members
        for member in circle_members:
            user_to_circle[member] = circle_id
        
        circle_counter += 1
    
    print(f"   ✅ Formed {circle_counter} primary circles with {len(assigned)} users")
    
    # Second pass: assign low-signal users to fallback circles
    print(f"\n🔍 Phase 2: Assigning {len(low_signal_users)} low-signal users to fallback circles...")
    for user_id in low_signal_users:
        user_profile = user_profiles[user_id]
        fallback_circle_id = _assign_to_fallback_circle(user_id, user_profile)
        
        circles[fallback_circle_id].append(user_id)
        user_to_circle[user_id] = fallback_circle_id
        assigned.add(user_id)
    
    # Third pass: assign remaining unassigned high-signal users who didn't match
    unassigned = set(user_ids) - assigned
    if unassigned:
        print(f"\n🔍 Phase 3: Assigning {len(unassigned)} unmatched users to fallback circles...")
        for user_id in unassigned:
            user_profile = user_profiles[user_id]
            fallback_circle_id = _assign_to_fallback_circle(user_id, user_profile)
            
            circles[fallback_circle_id].append(user_id)
            user_to_circle[user_id] = fallback_circle_id
            assigned.add(user_id)
    
    # Clean up empty fallback circles
    empty_fallbacks = [cid for cid, members in circles.items() if cid.startswith("fallback_") and not members]
    for cid in empty_fallbacks:
        del circles[cid]
    
    # Summary
    fallback_count = sum(1 for cid in circles.keys() if cid.startswith("fallback_"))
    fallback_users = sum(len(members) for cid, members in circles.items() if cid.startswith("fallback_"))
    
    print(f"\n✅ Final: {len(circles)} total circles ({circle_counter} primary + {fallback_count} fallback)")
    print(f"   📊 {len(assigned)} total users ({len(assigned) - fallback_users} in primary, {fallback_users} in fallback)")


def _simulate_interactions():
    """Simulate recent interaction events for demo"""
    global interaction_log
    
    now = datetime.now()
    
    # Generate interactions for last 14 days
    for user_id, circle_id in user_to_circle.items():
        user_orders = orders_df[orders_df['customer_id'] == user_id]
        
        if len(user_orders) > 0:
            # Simulate some recent interactions
            sample_skus = user_orders['sku'].sample(min(3, len(user_orders))).tolist()
            
            for sku in sample_skus:
                # Random events in past 14 days
                days_ago = hash(f"{user_id}{sku}") % 14
                timestamp = (now - timedelta(days=days_ago)).isoformat()
                
                # Purchase event
                interaction_log.append({
                    "user_id": user_id,
                    "sku": str(sku),
                    "event_type": "purchase",
                    "timestamp": timestamp
                })
                
                # Add view/like events before purchase
                for event_type in ["view", "like", "cart"]:
                    interaction_log.append({
                        "user_id": user_id,
                        "sku": str(sku),
                        "event_type": event_type,
                        "timestamp": (now - timedelta(days=days_ago+1)).isoformat()
                    })
    
    print(f"✅ Simulated {len(interaction_log)} interaction events")


# ==================== TREND DETECTION ====================

def _detect_circle_trends(circle_id: str, days: int = 14) -> List[Dict]:
    """Detect trending products in a circle (with chat amplification)"""
    circle_users = set(circles.get(circle_id, []))
    
    if not circle_users:
        return []
    
    # Filter interactions for this circle in time window
    cutoff = datetime.now() - timedelta(days=days)
    
    sku_scores = defaultdict(lambda: {
        "score": 0,
        "interactions": [],
        "users": set()
    })
    
    for event in interaction_log:
        if event['user_id'] not in circle_users:
            continue
        
        event_time = datetime.fromisoformat(event['timestamp'])
        if event_time < cutoff:
            continue
        
        sku = event['sku']
        weight = INTERACTION_WEIGHTS.get(event['event_type'], 1)
        
        # Recency boost
        days_old = (datetime.now() - event_time).days
        recency_factor = 1 / (1 + days_old * 0.1)
        
        sku_scores[sku]["score"] += weight * recency_factor
        sku_scores[sku]["interactions"].append(event)
        sku_scores[sku]["users"].add(event['user_id'])
    
    # CHAT AMPLIFICATION: Add chat mention signals
    chat_mentions = _extract_mentions_from_chat(circle_id, hours=24)
    for sku, mention_count in chat_mentions.items():
        if sku in sku_scores:
            sku_scores[sku]["score"] += mention_count * CHAT_MENTION_WEIGHT
    
    # Convert to list and enrich with product data
    trends = []
    for sku, data in sku_scores.items():
        product = products_df[products_df['sku'] == sku]
        
        if len(product) == 0:
            continue
        
        product = product.iloc[0]
        
        # Calculate velocity (interactions per day)
        interaction_days = set()
        for event in data['interactions']:
            event_time = datetime.fromisoformat(event['timestamp'])
            interaction_days.add(event_time.date())
        
        velocity = len(data['interactions']) / max(len(interaction_days), 1)
        
        # Determine trend label
        trend_label = _classify_trend(data['score'], velocity, len(data['users']))
        
        trends.append({
            "sku": sku,
            "product_name": product['ProductDisplayName'],
            "brand": product['brand'],
            "score": data['score'],
            "trend_label": trend_label,
            "interaction_count": len(data['interactions']),
            "velocity": velocity,
            "unique_users": len(data['users'])
        })
    
    # Sort by score
    trends.sort(key=lambda x: x['score'], reverse=True)
    
    return trends[:20]


def _classify_trend(score: float, velocity: float, user_count: int) -> str:
    """Classify trend momentum"""
    if velocity > 2 and user_count > 3:
        return "Rising"
    elif score > 30:
        return "Peaking"
    elif user_count >= 2 and velocity > 1:
        return "Emerging"
    else:
        return "Stable"


def _predict_trends(circle_id: str) -> List[Dict]:
    """Predict next 7-day trends"""
    current_trends = _detect_circle_trends(circle_id, days=7)
    
    predictions = []
    for trend in current_trends:
        # Simple momentum prediction
        if trend['velocity'] > 1.5:
            prediction_score = trend['score'] * 1.3
            prediction_label = "Rising"
        elif trend['trend_label'] == "Emerging":
            prediction_score = trend['score'] * 1.5
            prediction_label = "Breakthrough"
        else:
            prediction_score = trend['score'] * 0.9
            prediction_label = "Steady"
        
        predictions.append({
            **trend,
            "predicted_score": prediction_score,
            "prediction_label": prediction_label
        })
    
    predictions.sort(key=lambda x: x['predicted_score'], reverse=True)
    return predictions[:10]


# ==================== AI EXPLANATIONS ====================

def _generate_explanation(user_id: str, sku: str, trend_data: Dict) -> str:
    """Generate AI explanation using Gemini"""
    if not GEMINI_API_KEY:
        return _fallback_explanation(trend_data)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        circle_id = user_to_circle.get(user_id, "")
        circle_users = circles.get(circle_id, [])
        user_profile = user_profiles.get(user_id, {})
        
        prompt = f"""Generate a brief, enthusiastic product recommendation explanation (2-3 sentences max).

Product: {trend_data.get('product_name', 'this item')}
Brand: {trend_data.get('brand', '')}
Trend: {trend_data.get('trend_label', 'popular')}

Context:
- {trend_data.get('unique_users', 0)} people in your style circle interacted with this
- User's preferred brands: {', '.join(user_profile.get('top_brands', [])[:2])}
- User's style: {', '.join(user_profile.get('top_categories', [])[:2])}

Write a compelling, personalized reason why this is perfect for them. Be specific about the social proof and style match. Sound excited but natural."""

        response = model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        print(f"⚠️ Gemini error: {e}")
        return _fallback_explanation(trend_data)


def _fallback_explanation(trend_data: Dict) -> str:
    """Fallback template explanation"""
    users = trend_data.get('unique_users', 0)
    trend = trend_data.get('trend_label', 'popular').lower()
    product = trend_data.get('product_name', 'this item')
    
    templates = [
        f"{users} people in your style circle are loving this {trend} pick right now.",
        f"This {trend} item matches your usual style — {users} similar shoppers already grabbed it.",
        f"Trending with {users} people who share your taste. {product} is a hot pick this week!",
    ]
    
    return templates[hash(trend_data.get('sku', '')) % len(templates)]


# ==================== CHAT FUNCTIONS ====================

def _generate_alias(user_id: str, circle_id: str) -> str:
    """Generate consistent anonymous alias for user in circle"""
    key = (user_id, circle_id)
    if key in user_aliases:
        return user_aliases[key]
    
    # Generate deterministic but anonymous alias
    hash_val = hash(f"{user_id}_{circle_id}") % 10000
    alias = f"StyleFan_{hash_val}"
    user_aliases[key] = alias
    return alias


def _contains_profanity(text: str) -> bool:
    """Check if text contains profanity"""
    text_lower = text.lower()
    return any(word in text_lower for word in PROFANITY_LIST)


def _check_rate_limit(user_id: str) -> bool:
    """Check if user has exceeded message rate limit"""
    now = datetime.now()
    cutoff = now - timedelta(minutes=1)
    
    if user_id not in user_message_timestamps:
        user_message_timestamps[user_id] = []
    
    # Remove old timestamps
    user_message_timestamps[user_id] = [
        ts for ts in user_message_timestamps[user_id] if ts > cutoff
    ]
    
    # Check limit
    if len(user_message_timestamps[user_id]) >= MAX_MESSAGES_PER_MINUTE:
        return False
    
    # Add current timestamp
    user_message_timestamps[user_id].append(now)
    return True


def _validate_message(text: str, last_messages: List[Dict]) -> tuple[bool, str]:
    """Validate message content and check for spam"""
    # Length check
    if len(text) < MIN_MESSAGE_LENGTH:
        return False, "Message too short"
    if len(text) > MAX_MESSAGE_LENGTH:
        return False, "Message too long"
    
    # Profanity check
    if _contains_profanity(text):
        return False, "Message contains inappropriate content"
    
    # Spam check - detect repeated messages
    if last_messages:
        recent_texts = [msg['text'] for msg in last_messages[-5:]]
        if recent_texts.count(text) > 0:
            return False, "Duplicate message detected"
    
    return True, "OK"


def _extract_mentions_from_chat(circle_id: str, hours: int = 1) -> Dict[str, int]:
    """Extract product mentions from recent chat messages"""
    if circle_id not in circle_chats:
        return {}
    
    cutoff = datetime.now() - timedelta(hours=hours)
    mentions = defaultdict(int)
    
    messages = circle_chats[circle_id]
    
    for msg in messages:
        if msg['type'] != 'user':
            continue
        
        msg_time = datetime.fromisoformat(msg['timestamp'])
        if msg_time < cutoff:
            continue
        
        text_lower = msg['text'].lower()
        
        # Match against product names and brands
        for _, product in products_df.iterrows():
            product_name = product['ProductDisplayName'].lower()
            brand = product['brand'].lower()
            sku = product['sku']
            
            # Check for brand mentions
            if brand in text_lower:
                mentions[sku] += 1
            
            # Check for product keywords (simple matching)
            product_words = set(product_name.split()[:3])  # First 3 words
            text_words = set(text_lower.split())
            if len(product_words & text_words) >= 2:  # At least 2 word overlap
                mentions[sku] += 1
    
    return dict(mentions)


def _should_post_ai_insight(circle_id: str) -> bool:
    """Check if enough time has passed to post new AI insight"""
    now = datetime.now()
    
    if circle_id not in ai_insight_timers:
        ai_insight_timers[circle_id] = now
        return True
    
    last_post = ai_insight_timers[circle_id]
    time_diff = (now - last_post).total_seconds() / 60
    
    return time_diff >= AI_INSIGHT_COOLDOWN_MINUTES


def _generate_ai_insight(circle_id: str) -> Optional[str]:
    """Generate AI insight based on circle trends and chat activity"""
    if not _should_post_ai_insight(circle_id):
        return None
    
    # Get recent trends
    trends = _detect_circle_trends(circle_id, days=3)
    
    # Get chat mentions
    chat_mentions = _extract_mentions_from_chat(circle_id, hours=2)
    
    # Combine signals
    insights = []
    
    # Trending product insights
    if trends:
        top_trend = trends[0]
        if top_trend['trend_label'] in ['Rising', 'Peaking']:
            users = top_trend.get('unique_users', 0)
            product = top_trend['product_name']
            brand = top_trend['brand']
            insights.append(
                f"🔥 {users} people in your circle viewed {brand} {product} recently"
            )
    
    # Chat mention insights
    if chat_mentions:
        top_mentioned_sku = max(chat_mentions, key=chat_mentions.get)
        mention_count = chat_mentions[top_mentioned_sku]
        product = products_df[products_df['sku'] == top_mentioned_sku].iloc[0]
        insights.append(
            f"💬 {product['brand']} is buzzing in chat — {mention_count} mentions in the last hour"
        )
    
    # Category trends
    if trends and len(trends) >= 3:
        categories = [t['product_name'].split()[0] for t in trends[:3]]
        if categories:
            insights.append(
                f"👀 Your circle is loving {', '.join(set(categories)[:2])} this week"
            )
    
    if insights:
        ai_insight_timers[circle_id] = datetime.now()
        return insights[0]  # Return most relevant
    
    return None


# ==================== API ENDPOINTS ====================

@app.get("/")
def root():
    return {
        "service": "Virtual Style Circles Agent",
        "version": "1.0.0",
        "status": "operational",
        "circles": len(circles),
        "users": len(user_profiles)
    }


@app.post("/circles/assign-user")
def assign_user_to_circle(user_id: str):
    """Manually assign or reassign user to a circle"""
    if user_id not in user_profiles:
        profile = _build_style_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User has no order history")
        user_profiles[user_id] = profile
    
    # Find best matching circle
    best_circle = None
    best_score = 0
    
    user_profile = user_profiles[user_id]
    
    for circle_id, members in circles.items():
        if len(members) >= MAX_CIRCLE_SIZE:
            continue
        
        # Calculate avg similarity to circle
        similarities = []
        for member_id in members[:5]:  # Sample 5 members
            member_profile = user_profiles[member_id]
            sim = _calculate_similarity(user_profile, member_profile)
            similarities.append(sim)
        
        avg_sim = sum(similarities) / len(similarities) if similarities else 0
        
        if avg_sim > best_score:
            best_score = avg_sim
            best_circle = circle_id
    
    # Assign to circle
    if best_circle and best_score >= SIMILARITY_THRESHOLD:
        circles[best_circle].append(user_id)
        user_to_circle[user_id] = best_circle
    else:
        # Create new circle
        new_circle_id = f"circle_{len(circles)}"
        circles[new_circle_id] = [user_id]
        user_to_circle[user_id] = new_circle_id
        best_circle = new_circle_id
    
    return {
        "user_id": user_id,
        "circle_id": best_circle,
        "similarity_score": best_score
    }


@app.get("/circles/{circle_id}")
def get_circle_info(circle_id: str):
    """Get circle information"""
    if circle_id not in circles:
        raise HTTPException(status_code=404, detail="Circle not found")
    
    members = circles[circle_id]
    
    # Aggregate circle stats
    all_brands = []
    all_categories = []
    all_prices = []
    
    for user_id in members:
        profile = user_profiles[user_id]
        all_brands.extend(profile['top_brands'])
        all_categories.extend(profile['top_categories'])
        all_prices.append(profile['avg_price'])
    
    brand_counts = Counter(all_brands)
    category_counts = Counter(all_categories)
    
    return {
        "circle_id": circle_id,
        "user_count": len(members),
        "avg_order_value": sum(all_prices) / len(all_prices) if all_prices else 0,
        "top_brands": [b for b, _ in brand_counts.most_common(5)],
        "top_categories": [c for c, _ in category_counts.most_common(5)]
    }


@app.get("/circles/{circle_id}/trends")
def get_circle_trends(circle_id: str, days: int = 14):
    """Get trending products in a circle"""
    if circle_id not in circles:
        raise HTTPException(status_code=404, detail="Circle not found")
    
    trends = _detect_circle_trends(circle_id, days)
    
    return {
        "circle_id": circle_id,
        "time_window_days": days,
        "trends": trends
    }


@app.get("/circles/{circle_id}/predict")
def predict_circle_trends(circle_id: str):
    """Predict next 7-day trends"""
    if circle_id not in circles:
        raise HTTPException(status_code=404, detail="Circle not found")
    
    predictions = _predict_trends(circle_id)
    
    return {
        "circle_id": circle_id,
        "prediction_horizon": "7 days",
        "predictions": predictions
    }


@app.get("/user/{user_id}/recommendations")
def get_user_recommendations(user_id: str, limit: int = 10):
    """Get personalized recommendations using circle trends"""
    if user_id not in user_to_circle:
        raise HTTPException(status_code=404, detail="User not found in any circle")
    
    circle_id = user_to_circle[user_id]
    trends = _detect_circle_trends(circle_id)
    
    if not trends:
        return {"user_id": user_id, "circle_id": circle_id, "recommendations": []}
    
    user_profile = user_profiles[user_id]
    
    recommendations = []
    for trend in trends[:limit]:
        sku = trend['sku']
        product = products_df[products_df['sku'] == sku].iloc[0]
        
        # Filter by price range
        price = product['price']
        min_price, max_price = user_profile['price_range']
        
        if price < min_price * 0.7 or price > max_price * 1.5:
            continue
        
        # Generate explanation
        explanation = _generate_explanation(user_id, sku, trend)
        
        recommendations.append({
            "sku": sku,
            "product_name": product['ProductDisplayName'],
            "brand": product['brand'],
            "price": float(price),
            "image_url": product.get('image_url', ''),
            "score": trend['score'],
            "explanation": explanation
        })
    
    return {
        "user_id": user_id,
        "circle_id": circle_id,
        "recommendations": recommendations[:limit]
    }


@app.post("/interactions/log")
def log_interaction(event: InteractionEvent):
    """Log user interaction event"""
    if not event.timestamp:
        event.timestamp = datetime.now().isoformat()
    
    interaction_log.append(event.dict())
    
    return {"status": "logged", "event": event}


# ==================== CHAT ENDPOINTS ====================

@app.post("/circle/{circle_id}/chat/send")
def send_chat_message(circle_id: str, message: ChatMessage):
    """Send a message to circle chat"""
    user_id = message.user_id
    
    # Validate circle exists
    if circle_id not in circles:
        raise HTTPException(status_code=404, detail="Circle not found")
    
    # Validate user is in circle
    if user_id not in circles[circle_id]:
        raise HTTPException(status_code=403, detail="User not in this circle")
    
    # Check rate limit
    if not _check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")
    
    # Initialize chat storage for circle if needed
    if circle_id not in circle_chats:
        circle_chats[circle_id] = []
    
    # Validate message
    is_valid, error_msg = _validate_message(message.text, circle_chats[circle_id])
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Generate alias
    alias = _generate_alias(user_id, circle_id)
    
    # Create message
    now = datetime.now()
    message_id = f"msg_{circle_id}_{int(now.timestamp() * 1000)}"
    
    chat_message = {
        "message_id": message_id,
        "circle_id": circle_id,
        "alias": alias,
        "text": message.text,
        "timestamp": now.isoformat(),
        "type": "user"
    }
    
    # Store message
    circle_chats[circle_id].append(chat_message)
    
    # Keep only last N messages
    if len(circle_chats[circle_id]) > MAX_MESSAGES_PER_CIRCLE:
        circle_chats[circle_id] = circle_chats[circle_id][-MAX_MESSAGES_PER_CIRCLE:]
    
    # Try to generate AI insight (will only post if cooldown passed)
    ai_insight = _generate_ai_insight(circle_id)
    ai_message = None
    
    if ai_insight:
        ai_message_id = f"ai_{circle_id}_{int(datetime.now().timestamp() * 1000)}"
        ai_message = {
            "message_id": ai_message_id,
            "circle_id": circle_id,
            "alias": "Style AI",
            "text": ai_insight,
            "timestamp": datetime.now().isoformat(),
            "type": "ai_insight"
        }
        circle_chats[circle_id].append(ai_message)
    
    return {
        "status": "sent",
        "message": chat_message,
        "ai_insight": ai_message
    }


@app.get("/circle/{circle_id}/chat/messages")
def get_chat_messages(circle_id: str, user_id: str, limit: int = 50):
    """Get recent chat messages for a circle"""
    # Validate circle exists
    if circle_id not in circles:
        raise HTTPException(status_code=404, detail="Circle not found")
    
    # Validate user is in circle
    if user_id not in circles[circle_id]:
        raise HTTPException(status_code=403, detail="User not in this circle")
    
    # Get messages
    messages = circle_chats.get(circle_id, [])
    
    # Return last N messages
    recent_messages = messages[-limit:] if len(messages) > limit else messages
    
    return {
        "circle_id": circle_id,
        "user_alias": _generate_alias(user_id, circle_id),
        "total_messages": len(messages),
        "messages": recent_messages
    }


@app.get("/stats")
def get_stats():
    """Get system statistics"""
    circle_sizes = [len(members) for members in circles.values()]
    
    return {
        "total_circles": len(circles),
        "total_users": len(user_profiles),
        "total_interactions": len(interaction_log),
        "avg_circle_size": sum(circle_sizes) / len(circle_sizes) if circle_sizes else 0,
        "largest_circle": max(circle_sizes) if circle_sizes else 0,
        "smallest_circle": min(circle_sizes) if circle_sizes else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)