"""
Redis utilities for Stylist Agent
"""
import redis
import os
import pandas as pd
from typing import Optional, Dict, List, Iterable
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
BASE_DIR = os.path.dirname(__file__)
PRODUCTS_CSV = os.path.join(BASE_DIR, "../../../data/products.csv")
INVENTORY_CSV = os.path.join(BASE_DIR, "../../../data/inventory.csv")

products_df = pd.read_csv(PRODUCTS_CSV)

# Normalize column names for new CSV schema
if "product_display_name" in products_df.columns and "ProductDisplayName" not in products_df.columns:
    products_df = products_df.rename(columns={"product_display_name": "ProductDisplayName"})
if "sub_category" in products_df.columns and "subcategory" not in products_df.columns:
    products_df = products_df.rename(columns={"sub_category": "subcategory"})

inventory_df = pd.read_csv(INVENTORY_CSV)
if "qty" in inventory_df.columns and "quantity" not in inventory_df.columns:
    inventory_df = inventory_df.rename(columns={"qty": "quantity"})

inventory_totals = (
    inventory_df
    .groupby("sku", as_index=False)["quantity"]
    .sum()
)

# Keep only SKUs that have available quantity across any channel
in_stock_products_df = (
    products_df.merge(
        inventory_totals[inventory_totals["quantity"] > 0],
        on="sku",
        how="inner"
    )
)


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
        "material": material,
        "quantity": int(inventory_totals[inventory_totals['sku'] == row['sku']]['quantity'].iloc[0]) if not inventory_totals[inventory_totals['sku'] == row['sku']].empty else 0
    }


def get_all_products() -> pd.DataFrame:
    """Get all products from catalog"""
    return products_df


def get_in_stock_products() -> pd.DataFrame:
    """Return merged product + inventory records that still have stock."""
    return in_stock_products_df.copy()


def _build_keyword_mask(series: pd.Series, keywords: Iterable[str]) -> pd.Series:
    if series.empty:
        return pd.Series(False, index=series.index)
    mask = pd.Series(False, index=series.index)
    for keyword in keywords:
        keyword_lower = str(keyword).strip().lower()
        if not keyword_lower:
            continue
        mask = mask | series.str.lower().str.contains(keyword_lower, na=False)
    return mask


def find_in_stock_products(
    category: Optional[str] = None,
    subcategory_keywords: Optional[Iterable[str]] = None,
    name_keywords: Optional[Iterable[str]] = None,
    exclude_skus: Optional[Iterable[str]] = None,
    limit: int = 3
) -> List[Dict]:
    """Lookup in-stock products using loose keyword filters."""

    df = get_in_stock_products()

    if category:
        df = df[df['category'].str.contains(str(category), case=False, na=False)]

    if subcategory_keywords:
        sub_mask = _build_keyword_mask(df['subcategory'], subcategory_keywords)
        name_mask = _build_keyword_mask(df['ProductDisplayName'], subcategory_keywords)
        df = df[sub_mask | name_mask]

    if name_keywords:
        name_mask = _build_keyword_mask(df['ProductDisplayName'], name_keywords)
        df = df[name_mask]

    if exclude_skus:
        exclude_set = {sku for sku in exclude_skus}
        df = df[~df['sku'].isin(exclude_set)]

    if df.empty:
        return []

    sort_columns = [col for col in ['quantity', 'ratings'] if col in df.columns]
    if sort_columns:
        df = df.sort_values(by=sort_columns, ascending=[False for _ in sort_columns], na_position='last')

    df_sorted = df.head(limit)

    results: List[Dict] = []
    for _, row in df_sorted.iterrows():
        results.append({
            "sku": row['sku'],
            "name": row['ProductDisplayName'],
            "brand": row.get('brand'),
            "category": row.get('category'),
            "subcategory": row.get('subcategory'),
            "price": row.get('price'),
            "quantity": int(row.get('quantity', 0)),
        })

    return results


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
