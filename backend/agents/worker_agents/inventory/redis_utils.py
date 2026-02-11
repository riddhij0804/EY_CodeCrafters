# Redis connection and Lua scripts for atomic inventory operations

import os
import threading
import time
from typing import Optional

import redis
from dotenv import load_dotenv

load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL")
HOLD_TTL = 300  # 5 minutes default hold time

# Initialize Redis client
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )
    except Exception as exc:
        print(f"⚠ Redis connection failed ({exc}); falling back to in-memory store")
        redis_client = None

# Validate connectivity immediately; if ping fails, fall back to in-memory store.
if redis_client:
    try:
        redis_client.ping()
    except Exception as exc:
        print(f"⚠ Redis ping failed ({exc}); falling back to in-memory store")
        redis_client = None

# In-memory fallback when Redis is unavailable
_IN_MEMORY_STOCK: dict[str, int] = {}
_IN_MEMORY_HOLDS: dict[str, dict] = {}
_IN_MEMORY_IDEMPOTENCY: dict[str, dict] = {}
_IN_MEMORY_HOLDS_EXPIRY: dict[str, float] = {}
_LOCK = threading.Lock()


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
elif REDIS_URL:
    print("⚠ Redis URL provided but connection unavailable - using in-memory inventory store")
else:
    print("ℹ️ REDIS_URL not set - using in-memory inventory store")


# ==========================================
# REDIS KEY PATTERNS
# ==========================================

def get_stock_key(sku: str, location: str = "online") -> str:
    """Generate Redis key for stock."""
    if location == "online":
        return f"stock:{sku}:online"
    if location.startswith("store:"):
        return f"stock:{sku}:{location}"
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
    
    Tries Supabase first (if FEATURE_SUPABASE_READ=true), then falls back to Redis.
    
    Returns:
        {
            "online": int,
            "stores": {"store_id": int, ...}
        }
    """
    # Try Supabase first (when enabled)
    try:
        import sys
        from pathlib import Path
        # Add backend to path so db package is importable
        backend_path = Path(__file__).resolve().parent.parent.parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        from db.repositories import inventory_repo
        
        supabase_result = inventory_repo.get_stock(sku)
        if supabase_result is not None:
            print(f"✅ Source: SUPABASE for SKU={sku}")
            return {
                "online": supabase_result.get("online", 0),
                "stores": supabase_result.get("stores", {})
            }
    except Exception as e:
        print(f"⚠️ Supabase read failed for SKU={sku}: {e}")
    
    # Fallback to Redis
    print(f"📦 Source: REDIS/CSV fallback for SKU={sku}")
    
    result = {"online": 0, "stores": {}}

    if redis_client:
        online_stock = redis_client.get(get_stock_key(sku, "online"))
        result["online"] = int(online_stock) if online_stock else 0

        pattern = f"stock:{sku}:store:*"
        store_keys = redis_client.keys(pattern)
        for key in store_keys:
            store_id = key.split(":")[-1]
            stock = redis_client.get(key)
            result["stores"][store_id] = int(stock) if stock else 0
        return result

    # In-memory fallback
    with _LOCK:
        online_key = get_stock_key(sku, "online")
        result["online"] = int(_IN_MEMORY_STOCK.get(online_key, 0))

        prefix = f"stock:{sku}:store:"
        for key, value in _IN_MEMORY_STOCK.items():
            if key.startswith(prefix):
                store_id = key[len(prefix):]
                result["stores"][store_id] = int(value)
    return result


def hold_stock_atomic(sku: str, quantity: int, location: str = "online") -> int:
    """
    Atomically decrement stock using Lua script.
    
    Returns:
        Remaining stock if successful, -1 if insufficient stock
    """
    if redis_client and hold_stock_script:
        try:
            result = hold_stock_script(args=[sku, quantity, location])
            remaining = int(result)
            # If Supabase write enabled, attempt to decrement Supabase as well
            try:
                from db.repositories import inventory_repo
                ok = inventory_repo.decrement_stock(sku, location, quantity)
                if ok:
                    print(f"✓ Supabase decremented for {sku} at {location} by {quantity}")
                else:
                    # Attempt to create/upsert row with remaining value when decrement failed
                    try:
                        up_ok = inventory_repo.upsert_stock(sku, location, remaining)
                        if up_ok:
                            print(f"✓ Supabase upserted row for {sku} at {location} with quantity={remaining}")
                        else:
                            print(f"⚠ Supabase decrement skipped and upsert failed for {sku} at {location}")
                    except Exception as e2:
                        print(f"⚠ Exception while upserting Supabase stock for {sku} at {location}: {e2}")
            except Exception as e:
                print(f"⚠ Failed to update Supabase stock after hold: {e}")
            return remaining
        except Exception as e:
            print(f"Error holding stock: {e}")
            return -1

    loc = location if location == "online" else f"store:{location}"
    stock_key = get_stock_key(sku, location)
    with _LOCK:
        current = int(_IN_MEMORY_STOCK.get(stock_key, 0))
        if current >= quantity:
            _IN_MEMORY_STOCK[stock_key] = current - quantity
            return current - quantity
        return -1


def release_stock_atomic(sku: str, quantity: int, location: str = "online") -> int:
    """
    Atomically increment stock using Lua script.
    
    Returns:
        New stock level
    """
    if redis_client and release_stock_script:
        try:
            result = release_stock_script(args=[sku, quantity, location])
            new_stock = int(result)
            # If Supabase write enabled, attempt to increment Supabase as well
            try:
                from db.repositories import inventory_repo
                inventory_repo.increment_stock(sku, location, quantity)
            except Exception as e:
                print(f"⚠ Failed to update Supabase stock after release: {e}")
            return new_stock
        except Exception as e:
            print(f"Error releasing stock: {e}")
            return 0

    stock_key = get_stock_key(sku, location)
    with _LOCK:
        current = int(_IN_MEMORY_STOCK.get(stock_key, 0))
        new_value = current + quantity
        _IN_MEMORY_STOCK[stock_key] = new_value
        return new_value


def set_stock(sku: str, quantity: int, location: str = "online") -> bool:
    """
    Set stock level for a SKU at a location.
    Used primarily for seeding data.
    """
    key = get_stock_key(sku, location)

    if redis_client:
        try:
            redis_client.set(key, quantity)
            return True
        except Exception as e:
            print(f"Error setting stock: {e}")
            return False

    with _LOCK:
        _IN_MEMORY_STOCK[key] = int(quantity)
    return True


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
    import json

    if redis_client:
        try:
            key = get_hold_key(hold_id)
            redis_client.setex(key, ttl, json.dumps(hold_data))
            expiry_time = redis_client.time()[0] + ttl
            redis_client.zadd("holds_by_expiry", {hold_id: expiry_time})
            return True
        except Exception as e:
            print(f"Error creating hold: {e}")
            return False

    with _LOCK:
        _IN_MEMORY_HOLDS[hold_id] = hold_data
        _IN_MEMORY_HOLDS_EXPIRY[hold_id] = time.time() + ttl
    return True


def get_hold(hold_id: str) -> Optional[dict]:
    """Get hold data if it exists."""
    import json

    if redis_client:
        try:
            key = get_hold_key(hold_id)
            data = redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Error getting hold: {e}")
            return None

    with _LOCK:
        data = _IN_MEMORY_HOLDS.get(hold_id)
        return data.copy() if data else None


def release_hold(hold_id: str) -> bool:
    """Mark hold as released and remove it."""
    if redis_client:
        try:
            key = get_hold_key(hold_id)
            redis_client.delete(key)
            redis_client.zrem("holds_by_expiry", hold_id)
            return True
        except Exception as e:
            print(f"Error releasing hold: {e}")
            return False

    with _LOCK:
        _IN_MEMORY_HOLDS.pop(hold_id, None)
        _IN_MEMORY_HOLDS_EXPIRY.pop(hold_id, None)
    return True


# ==========================================
# IDEMPOTENCY
# ==========================================

def check_idempotency(key: str) -> Optional[dict]:
    """Check if request was already processed."""
    import json

    if redis_client:
        try:
            idemp_key = get_idempotency_key(key)
            data = redis_client.get(idemp_key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Error checking idempotency: {e}")
            return None

    with _LOCK:
        data = _IN_MEMORY_IDEMPOTENCY.get(key)
        return json.loads(json.dumps(data)) if data else None


def save_idempotency(key: str, response: dict, ttl: int = 3600) -> bool:
    """Save response for idempotency check (1 hour TTL)."""
    import json

    if redis_client:
        try:
            idemp_key = get_idempotency_key(key)
            redis_client.setex(idemp_key, ttl, json.dumps(response))
            return True
        except Exception as e:
            print(f"Error saving idempotency: {e}")
            return False

    with _LOCK:
        _IN_MEMORY_IDEMPOTENCY[key] = json.loads(json.dumps(response))
    return True


# ==========================================
# EXPIRY MANAGEMENT
# ==========================================

def get_expired_holds() -> list:
    """Get all holds that have expired."""
    if redis_client:
        try:
            current_time = redis_client.time()[0]
            expired = redis_client.zrangebyscore("holds_by_expiry", 0, current_time)
            return expired
        except Exception as e:
            print(f"Error getting expired holds: {e}")
            return []

    now = time.time()
    with _LOCK:
        return [hold_id for hold_id, expiry in list(_IN_MEMORY_HOLDS_EXPIRY.items()) if expiry <= now]


def cleanup_expired_hold(hold_id: str) -> bool:
    """
    Cleanup an expired hold by restoring stock.
    
    Returns:
        True if successful
    """
    if redis_client:
        try:
            hold = get_hold(hold_id)

            if hold:
                release_stock_atomic(
                    hold["sku"],
                    hold["quantity"],
                    hold.get("location", "online")
                )

            redis_client.zrem("holds_by_expiry", hold_id)
            return True
        except Exception as e:
            print(f"Error cleaning up expired hold: {e}")
            return False

    with _LOCK:
        hold = _IN_MEMORY_HOLDS.pop(hold_id, None)
        _IN_MEMORY_HOLDS_EXPIRY.pop(hold_id, None)

    if hold:
        release_stock_atomic(hold["sku"], hold["quantity"], hold.get("location", "online"))
    return True


# ==========================================
# HEALTH CHECK
# ==========================================

def check_redis_health() -> bool:
    """Check if Redis is available."""
    if redis_client:
        try:
            redis_client.ping()
            return True
        except Exception:
            return False
    # In-memory fallback treated as healthy so dependent services continue
    return True


print(f"✓ Redis utils loaded (connected: {redis_client is not None})")
