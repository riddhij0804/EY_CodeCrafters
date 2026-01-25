"""
Redis utilities for Post-Purchase Agent
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import redis
from redis.exceptions import RedisError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL")

# Initialize Redis client
redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5
) if REDIS_URL else None

# In-memory fallback stores when Redis is unavailable
IN_MEMORY_ORDERS: Dict[str, Dict] = {}
IN_MEMORY_USER_ORDERS: Dict[str, set] = {}
IN_MEMORY_RETURNS: Dict[str, Dict] = {}
IN_MEMORY_USER_RETURNS: Dict[str, List[str]] = {}
IN_MEMORY_EXCHANGES: Dict[str, Dict] = {}
IN_MEMORY_USER_EXCHANGES: Dict[str, List[str]] = {}
IN_MEMORY_COMPLAINTS: Dict[str, Dict] = {}
IN_MEMORY_USER_COMPLAINTS: Dict[str, List[str]] = {}
IN_MEMORY_FEEDBACK: Dict[str, Dict] = {}
IN_MEMORY_USER_FEEDBACK: Dict[str, List[str]] = {}

# Load orders and products data
ORDERS_CSV = os.path.join(os.path.dirname(__file__), "../../../data/orders.csv")
PRODUCTS_CSV = os.path.join(os.path.dirname(__file__), "../../../data/products.csv")

orders_df = pd.read_csv(ORDERS_CSV)
products_df = pd.read_csv(PRODUCTS_CSV)


def _get_dynamic_order(order_id: str) -> Optional[Dict]:
    """Fetch dynamically registered order from Redis."""
    if redis_client:
        dynamic_key = f"dynamic_order:{order_id}"
        raw = redis_client.get(dynamic_key)
        if not raw:
            return None

        try:
            order_data = json.loads(raw)
            # Normalize basic types
            order_data["customer_id"] = str(order_data.get("customer_id", ""))
            order_data.setdefault("items", [])
            order_data.setdefault("status", "completed")
            order_data.setdefault("total_amount", 0)
            order_data.setdefault("created_at", datetime.utcnow().isoformat())
            return order_data
        except json.JSONDecodeError:
            return None

    # Fallback to in-memory store
    order_data = IN_MEMORY_ORDERS.get(order_id)
    if order_data:
        return order_data

    return None


def get_order_details(order_id: str) -> Optional[Dict]:
    """Get order details from orders.csv or dynamically registered orders."""
    order = orders_df[orders_df['order_id'] == order_id]

    if order.empty:
        dynamic = _get_dynamic_order(order_id)
        if dynamic:
            return dynamic
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
    
    if redis_client:
        try:
            dynamic_ids = redis_client.smembers(f"user:{user_id}:orders")
        except RedisError as exc:
            logger.warning("Redis smembers failed for user %s: %s", user_id, exc)
            dynamic_ids = set()
    else:
        dynamic_ids = IN_MEMORY_USER_ORDERS.get(str(user_id), set())

    for order_id in dynamic_ids:
        dynamic = _get_dynamic_order(order_id)
        if dynamic:
            orders_list.append({
                "order_id": dynamic.get("order_id"),
                "total_amount": dynamic.get("total_amount"),
                "status": dynamic.get("status", "completed"),
                "created_at": dynamic.get("created_at"),
            })
    
    return orders_list
    
    return order_data if order_data else None


def store_dynamic_order(order_data: Dict) -> Dict:
    """Persist dynamically generated order so returns/exchanges can reference it."""
    required_fields = {"order_id", "customer_id", "items"}
    if not required_fields.issubset(order_data.keys()):
        missing = required_fields - set(order_data.keys())
        raise ValueError(f"Missing required order fields: {missing}")

    order_id = order_data["order_id"]
    normalized = {
        "order_id": order_id,
        "customer_id": str(order_data.get("customer_id")),
        "items": order_data.get("items", []),
        "total_amount": float(order_data.get("total_amount", 0)),
        "status": order_data.get("status", "completed"),
        "created_at": order_data.get("created_at") or datetime.utcnow().isoformat(),
        "shipping_address": order_data.get("shipping_address", {}),
        "metadata": order_data.get("metadata", {}),
    }

    if redis_client:
        try:
            redis_client.set(f"dynamic_order:{order_id}", json.dumps(normalized))
            redis_client.sadd(f"user:{normalized['customer_id']}:orders", order_id)
            return normalized
        except RedisError as exc:
            logger.warning("Redis unavailable while storing dynamic order %s: %s", order_id, exc)

    IN_MEMORY_ORDERS[order_id] = normalized
    IN_MEMORY_USER_ORDERS.setdefault(normalized['customer_id'], set()).add(order_id)

    return normalized


def store_return_request(return_id: str, return_data: Dict) -> bool:
    """Store return request in Redis"""
    user_id = return_data.get("user_id")

    if redis_client:
        try:
            return_key = f"return:{return_id}"
            redis_client.hset(return_key, mapping=return_data)
            if user_id:
                redis_client.lpush(f"user:{user_id}:returns", return_id)
            return True
        except RedisError as exc:
            logger.warning("Redis unavailable while storing return %s: %s", return_id, exc)

    IN_MEMORY_RETURNS[return_id] = return_data
    if user_id:
        IN_MEMORY_USER_RETURNS.setdefault(str(user_id), []).insert(0, return_id)
    
    return True


def store_exchange_request(exchange_id: str, exchange_data: Dict) -> bool:
    """Store exchange request in Redis"""
    user_id = exchange_data.get("user_id")

    if redis_client:
        try:
            exchange_key = f"exchange:{exchange_id}"
            redis_client.hset(exchange_key, mapping=exchange_data)
            if user_id:
                redis_client.lpush(f"user:{user_id}:exchanges", exchange_id)
            return True
        except RedisError as exc:
            logger.warning("Redis unavailable while storing exchange %s: %s", exchange_id, exc)

    IN_MEMORY_EXCHANGES[exchange_id] = exchange_data
    if user_id:
        IN_MEMORY_USER_EXCHANGES.setdefault(str(user_id), []).insert(0, exchange_id)
    
    return True


def store_complaint(complaint_id: str, complaint_data: Dict) -> bool:
    """Store complaint/issue in Redis"""
    user_id = complaint_data.get("user_id")

    if redis_client:
        try:
            complaint_key = f"complaint:{complaint_id}"
            redis_client.hset(complaint_key, mapping=complaint_data)
            if user_id:
                redis_client.lpush(f"user:{user_id}:complaints", complaint_id)
            return True
        except RedisError as exc:
            logger.warning("Redis unavailable while storing complaint %s: %s", complaint_id, exc)

    IN_MEMORY_COMPLAINTS[complaint_id] = complaint_data
    if user_id:
        IN_MEMORY_USER_COMPLAINTS.setdefault(str(user_id), []).insert(0, complaint_id)
    
    return True


def store_feedback(feedback_id: str, feedback_data: Dict) -> bool:
    """Store post-purchase feedback"""
    user_id = feedback_data.get("user_id")

    if redis_client:
        try:
            feedback_key = f"feedback:{feedback_id}"
            redis_client.hset(feedback_key, mapping=feedback_data)
            if user_id:
                redis_client.lpush(f"user:{user_id}:feedback", feedback_id)
            return True
        except RedisError as exc:
            logger.warning("Redis unavailable while storing feedback %s: %s", feedback_id, exc)

    IN_MEMORY_FEEDBACK[feedback_id] = feedback_data
    if user_id:
        IN_MEMORY_USER_FEEDBACK.setdefault(str(user_id), []).insert(0, feedback_id)

    return True


def get_return_request(return_id: str) -> Optional[Dict]:
    """Get return request details"""
    if redis_client:
        try:
            return_key = f"return:{return_id}"
            return_data = redis_client.hgetall(return_key)
            if return_data:
                return return_data
        except RedisError as exc:
            logger.warning("Redis unavailable while fetching return %s: %s", return_id, exc)
    else:
        return_data = IN_MEMORY_RETURNS.get(return_id)
        if return_data:
            return return_data

    return None


def get_user_returns(user_id: str, limit: int = 10) -> list:
    """Get user's return history"""
    if redis_client:
        try:
            return_ids = redis_client.lrange(f"user:{user_id}:returns", 0, limit - 1)
        except RedisError as exc:
            logger.warning("Redis unavailable while fetching return history for %s: %s", user_id, exc)
            return_ids = []
    else:
        return_ids = IN_MEMORY_USER_RETURNS.get(str(user_id), [])[:limit]
    
    returns = []
    for return_id in return_ids:
        return_data = get_return_request(return_id)
        if return_data:
            return_data["return_id"] = return_id
            returns.append(return_data)
    
    return returns
