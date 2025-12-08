"""
Redis utilities for Stylist Agent
"""
import redis
import os
import pandas as pd
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL")

# Initialize Redis client
redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5
) if REDIS_URL else None

# Load product catalog
PRODUCTS_CSV = os.path.join(os.path.dirname(__file__), "../../../data/products.csv")
products_df = pd.read_csv(PRODUCTS_CSV)


def get_product_details(sku: str) -> Optional[Dict]:
    """Get product details from products.csv"""
    product = products_df[products_df['sku'] == sku]
    if product.empty:
        return None
    
    row = product.iloc[0]
    
    # Safely parse attributes (handle null/None values)
    color = 'N/A'
    material = 'N/A'
    if pd.notna(row['attributes']) and str(row['attributes']).lower() not in ['null', 'none', '']:
        try:
            import ast
            attrs = ast.literal_eval(row['attributes'])
            color = attrs.get('color', 'N/A')
            material = attrs.get('material', 'N/A')
        except:
            pass
    
    return {
        "sku": row['sku'],
        "name": row['ProductDisplayName'],
        "brand": row['brand'] if pd.notna(row['brand']) else 'N/A',
        "category": row['category'],
        "subcategory": row['subcategory'],
        "price": row['price'],
        "color": color,
        "material": material
    }


def get_all_products() -> pd.DataFrame:
    """Get all products from catalog"""
    return products_df


def search_products_by_category(category: str, subcategory: str = None, limit: int = 5) -> List[Dict]:
    """Search products by category for recommendations"""
    filtered = products_df[products_df['category'].str.lower() == category.lower()]
    
    if subcategory:
        filtered = filtered[filtered['subcategory'].str.lower() == subcategory.lower()]
    
    # Get random products
    sample = filtered.sample(n=min(limit, len(filtered))) if len(filtered) > 0 else pd.DataFrame()
    
    results = []
    for _, row in sample.iterrows():
        results.append({
            "sku": row['sku'],
            "name": row['ProductDisplayName'],
            "brand": row['brand'],
            "price": row['price'],
            "category": row['category'],
            "subcategory": row['subcategory']
        })
    
    return results


def store_styling_recommendation(recommendation_id: str, data: Dict) -> bool:
    """Store styling recommendation in Redis"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    key = f"styling:{recommendation_id}"
    redis_client.hset(key, mapping=data)
    return True


def get_user_purchase_history(user_id: str) -> List[Dict]:
    """Get user's purchase history from orders.csv"""
    orders_csv = os.path.join(os.path.dirname(__file__), "../../../data/orders.csv")
    orders_df = pd.read_csv(orders_csv)
    
    user_orders = orders_df[orders_df['customer_id'] == int(user_id)]
    
    purchases = []
    for _, order in user_orders.iterrows():
        try:
            import ast
            items = ast.literal_eval(order['items'])
            for item in items:
                product = get_product_details(item['sku'])
                if product:
                    purchases.append(product)
        except:
            continue
    
    return purchases


def store_user_fit_feedback(user_id: str, sku: str, feedback: Dict) -> bool:
    """Store user's fit feedback for future recommendations"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    key = f"fit_feedback:{user_id}:{sku}"
    redis_client.hset(key, mapping=feedback)
    return True
