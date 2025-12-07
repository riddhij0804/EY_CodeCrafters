# Redis connection and Lua scripts for atomic inventory operations

import redis
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL")
HOLD_TTL = 300  # 5 minutes default hold time

# Initialize Redis client
redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5
) if REDIS_URL else None


# ==========================================
# LUA SCRIPTS FOR ATOMIC OPERATIONS
# ==========================================

# Atomic stock decrement (hold inventory)
LUA_HOLD_STOCK = """
local sku = ARGV[1]
local quantity = tonumber(ARGV[2])
local location = ARGV[3]  -- 'online' or 'store:{store_id}'

local key
if location == 'online' then
    key = 'stock:' .. sku .. ':online'
else
    key = 'stock:' .. sku .. ':' .. location
end

local current = tonumber(redis.call('GET', key) or 0)

if current >= quantity then
    redis.call('DECRBY', key, quantity)
    return current - quantity
else
    return -1  -- Insufficient stock
end
"""

# Atomic stock increment (release hold)
LUA_RELEASE_STOCK = """
local sku = ARGV[1]
local quantity = tonumber(ARGV[2])
local location = ARGV[3]

local key
if location == 'online' then
    key = 'stock:' .. sku .. ':online'
else
    key = 'stock:' .. sku .. ':' .. location
end

redis.call('INCRBY', key, quantity)
return tonumber(redis.call('GET', key))
"""

# Register Lua scripts
hold_stock_script = None
release_stock_script = None

if redis_client:
    try:
        hold_stock_script = redis_client.register_script(LUA_HOLD_STOCK)
        release_stock_script = redis_client.register_script(LUA_RELEASE_STOCK)
        print("✓ Lua scripts registered successfully")
    except Exception as e:
        print(f"⚠ Failed to register Lua scripts: {e}")


# ==========================================
# REDIS KEY PATTERNS
# ==========================================

def get_stock_key(sku: str, location: str = "online") -> str:
    """Generate Redis key for stock."""
    if location == "online":
        return f"stock:{sku}:online"
    else:
        return f"stock:{sku}:store:{location}"


def get_hold_key(hold_id: str) -> str:
    """Generate Redis key for hold."""
    return f"hold:{hold_id}"


def get_idempotency_key(key: str) -> str:
    """Generate Redis key for idempotency."""
    return f"idemp:{key}"


# ==========================================
# STOCK OPERATIONS
# ==========================================

def get_stock(sku: str) -> dict:
    """
    Get stock levels for a SKU across all locations.
    
    Returns:
        {
            "online": int,
            "stores": {"store_id": int, ...}
        }
    """
    if not redis_client:
        return {"online": 0, "stores": {}}
    
    result = {"online": 0, "stores": {}}
    
    # Get online stock
    online_stock = redis_client.get(get_stock_key(sku, "online"))
    result["online"] = int(online_stock) if online_stock else 0
    
    # Get store stocks
    pattern = f"stock:{sku}:store:*"
    store_keys = redis_client.keys(pattern)
    
    for key in store_keys:
        store_id = key.split(":")[-1]
        stock = redis_client.get(key)
        result["stores"][store_id] = int(stock) if stock else 0
    
    return result


def hold_stock_atomic(sku: str, quantity: int, location: str = "online") -> int:
    """
    Atomically decrement stock using Lua script.
    
    Returns:
        Remaining stock if successful, -1 if insufficient stock
    """
    if not redis_client or not hold_stock_script:
        return -1
    
    try:
        result = hold_stock_script(args=[sku, quantity, location])
        return int(result)
    except Exception as e:
        print(f"Error holding stock: {e}")
        return -1


def release_stock_atomic(sku: str, quantity: int, location: str = "online") -> int:
    """
    Atomically increment stock using Lua script.
    
    Returns:
        New stock level
    """
    if not redis_client or not release_stock_script:
        return 0
    
    try:
        result = release_stock_script(args=[sku, quantity, location])
        return int(result)
    except Exception as e:
        print(f"Error releasing stock: {e}")
        return 0


def set_stock(sku: str, quantity: int, location: str = "online") -> bool:
    """
    Set stock level for a SKU at a location.
    Used primarily for seeding data.
    """
    if not redis_client:
        return False
    
    try:
        key = get_stock_key(sku, location)
        redis_client.set(key, quantity)
        return True
    except Exception as e:
        print(f"Error setting stock: {e}")
        return False


# ==========================================
# HOLD OPERATIONS
# ==========================================

def create_hold(hold_id: str, hold_data: dict, ttl: int = HOLD_TTL) -> bool:
    """
    Create a hold with TTL.
    
    Args:
        hold_id: Unique hold identifier
        hold_data: Hold information (sku, quantity, location, etc.)
        ttl: Time to live in seconds
    
    Returns:
        True if successful
    """
    if not redis_client:
        return False
    
    try:
        import json
        key = get_hold_key(hold_id)
        redis_client.setex(key, ttl, json.dumps(hold_data))
        
        # Add to sorted set for expiry tracking
        expiry_time = redis_client.time()[0] + ttl
        redis_client.zadd("holds_by_expiry", {hold_id: expiry_time})
        
        return True
    except Exception as e:
        print(f"Error creating hold: {e}")
        return False


def get_hold(hold_id: str) -> Optional[dict]:
    """Get hold data if it exists."""
    if not redis_client:
        return None
    
    try:
        import json
        key = get_hold_key(hold_id)
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"Error getting hold: {e}")
        return None


def release_hold(hold_id: str) -> bool:
    """Mark hold as released and remove it."""
    if not redis_client:
        return False
    
    try:
        key = get_hold_key(hold_id)
        redis_client.delete(key)
        redis_client.zrem("holds_by_expiry", hold_id)
        return True
    except Exception as e:
        print(f"Error releasing hold: {e}")
        return False


# ==========================================
# IDEMPOTENCY
# ==========================================

def check_idempotency(key: str) -> Optional[dict]:
    """Check if request was already processed."""
    if not redis_client:
        return None
    
    try:
        import json
        idemp_key = get_idempotency_key(key)
        data = redis_client.get(idemp_key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"Error checking idempotency: {e}")
        return None


def save_idempotency(key: str, response: dict, ttl: int = 3600) -> bool:
    """Save response for idempotency check (1 hour TTL)."""
    if not redis_client:
        return False
    
    try:
        import json
        idemp_key = get_idempotency_key(key)
        redis_client.setex(idemp_key, ttl, json.dumps(response))
        return True
    except Exception as e:
        print(f"Error saving idempotency: {e}")
        return False


# ==========================================
# EXPIRY MANAGEMENT
# ==========================================

def get_expired_holds() -> list:
    """Get all holds that have expired."""
    if not redis_client:
        return []
    
    try:
        current_time = redis_client.time()[0]
        # Get all holds with expiry time <= current time
        expired = redis_client.zrangebyscore("holds_by_expiry", 0, current_time)
        return expired
    except Exception as e:
        print(f"Error getting expired holds: {e}")
        return []


def cleanup_expired_hold(hold_id: str) -> bool:
    """
    Cleanup an expired hold by restoring stock.
    
    Returns:
        True if successful
    """
    if not redis_client:
        return False
    
    try:
        # Get hold data
        hold = get_hold(hold_id)
        
        if hold:
            # Restore stock
            release_stock_atomic(
                hold["sku"],
                hold["quantity"],
                hold.get("location", "online")
            )
        
        # Remove from expiry tracking
        redis_client.zrem("holds_by_expiry", hold_id)
        
        return True
    except Exception as e:
        print(f"Error cleaning up expired hold: {e}")
        return False


# ==========================================
# HEALTH CHECK
# ==========================================

def check_redis_health() -> bool:
    """Check if Redis is available."""
    if not redis_client:
        return False
    
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


print(f"✓ Redis utils loaded (connected: {check_redis_health()})")
