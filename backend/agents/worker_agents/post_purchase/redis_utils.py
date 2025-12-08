"""
Redis utilities for Post-Purchase Agent
"""
import redis
import os
import pandas as pd
from typing import Optional, Dict, List
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL")

# Initialize Redis client
redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5
) if REDIS_URL else None

# Load orders and products data
ORDERS_CSV = os.path.join(os.path.dirname(__file__), "../../../data/orders.csv")
PRODUCTS_CSV = os.path.join(os.path.dirname(__file__), "../../../data/products.csv")

orders_df = pd.read_csv(ORDERS_CSV)
products_df = pd.read_csv(PRODUCTS_CSV)


def get_order_details(order_id: str) -> Optional[Dict]:
    """Get order details from orders.csv"""
    order = orders_df[orders_df['order_id'] == order_id]
    
    if order.empty:
        return None
    
    row = order.iloc[0]
    items_raw = eval(row['items'])
    
    # Enrich items with product details
    enriched_items = []
    for item in items_raw:
        product = products_df[products_df['sku'] == item['sku']]
        if not product.empty:
            p = product.iloc[0]
            enriched_items.append({
                "sku": item['sku'],
                "name": p['ProductDisplayName'],
                "brand": p['brand'],
                "category": p['category'],
                "quantity": item['qty'],
                "unit_price": item['unit_price'],
                "line_total": item['line_total']
            })
    
    return {
        "order_id": row['order_id'],
        "customer_id": str(row['customer_id']),
        "items": enriched_items,
        "total_amount": row['total_amount'],
        "status": row['status'],
        "created_at": row['created_at']
    }


def get_user_orders(user_id: str) -> List[Dict]:
    """Get all orders for a user"""
    user_orders = orders_df[orders_df['customer_id'] == int(user_id)]
    
    orders_list = []
    for _, row in user_orders.iterrows():
        orders_list.append({
            "order_id": row['order_id'],
            "total_amount": row['total_amount'],
            "status": row['status'],
            "created_at": row['created_at']
        })
    
    return orders_list
    
    return order_data if order_data else None


def store_return_request(return_id: str, return_data: Dict) -> bool:
    """Store return request in Redis"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    return_key = f"return:{return_id}"
    redis_client.hset(return_key, mapping=return_data)
    
    # Add to user's return list
    user_id = return_data.get("user_id")
    if user_id:
        redis_client.lpush(f"user:{user_id}:returns", return_id)
    
    return True


def store_exchange_request(exchange_id: str, exchange_data: Dict) -> bool:
    """Store exchange request in Redis"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    exchange_key = f"exchange:{exchange_id}"
    redis_client.hset(exchange_key, mapping=exchange_data)
    
    # Add to user's exchange list
    user_id = exchange_data.get("user_id")
    if user_id:
        redis_client.lpush(f"user:{user_id}:exchanges", exchange_id)
    
    return True


def store_complaint(complaint_id: str, complaint_data: Dict) -> bool:
    """Store complaint/issue in Redis"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    complaint_key = f"complaint:{complaint_id}"
    redis_client.hset(complaint_key, mapping=complaint_data)
    
    # Add to user's complaint list
    user_id = complaint_data.get("user_id")
    if user_id:
        redis_client.lpush(f"user:{user_id}:complaints", complaint_id)
    
    return True


def get_return_request(return_id: str) -> Optional[Dict]:
    """Get return request details"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    return_key = f"return:{return_id}"
    return_data = redis_client.hgetall(return_key)
    
    return return_data if return_data else None


def get_user_returns(user_id: str, limit: int = 10) -> list:
    """Get user's return history"""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    
    return_ids = redis_client.lrange(f"user:{user_id}:returns", 0, limit - 1)
    
    returns = []
    for return_id in return_ids:
        return_data = get_return_request(return_id)
        if return_data:
            return_data["return_id"] = return_id
            returns.append(return_data)
    
    return returns
