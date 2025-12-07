# Inventory Agent - Redis-based Inventory Management

Atomic inventory operations with Redis, TTL-based holds, and idempotency support.

## 🚀 Features

- **Atomic Operations**: Lua scripts prevent race conditions
- **TTL-based Holds**: Automatic expiry with background cleanup
- **Idempotency**: Duplicate request prevention with 1-hour cache
- **Multi-location**: Online + store-specific inventory
- **Real-time**: Sub-millisecond Redis operations

## 📦 Installation

### 1. Install Dependencies

```bash
cd backend/agents/worker_agents/inventory
pip install fastapi uvicorn redis python-dotenv
```

### 2. Configure Redis

Add to `backend/.env`:

```env
REDIS_URL=rediss://default:YOUR_PASSWORD@your-redis-host:6379
```

### 3. Seed Inventory

Load CSV data into Redis:

```bash
python seed_inventory.py
```

Expected output:
```
✅ Redis connected
📦 Loading online inventory from merged_products_902_rows.csv...
  ✓ Loaded 902 SKUs...
🏬 Loading store inventory from inventory_realistic.csv...
  ✓ Loaded 4511 store entries...
✅ SEEDING COMPLETE
```

## 🔧 Usage

### Start Server

```bash
python app.py
```

Server runs on `http://localhost:8001`

### API Endpoints

#### 1. Get Inventory

```bash
GET /inventory/{sku}
```

**Example:**

```bash
curl http://localhost:8001/inventory/SKU000001
```

**Response:**

```json
{
  "sku": "SKU000001",
  "online_stock": 500,
  "store_stock": {
    "STORE_MUMBAI": 182,
    "STORE_DELHI": 249,
    "STORE_BANGALORE": 152,
    "STORE_PUNE": 54
  },
  "total_stock": 1137
}
```

#### 2. Create Hold

```bash
POST /hold
```

**Request:**

```json
{
  "sku": "SKU000001",
  "quantity": 3,
  "location": "online",
  "ttl": 300
}
```

**With Idempotency:**

```bash
curl -X POST http://localhost:8001/hold \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: order-12345" \
  -d '{
    "sku": "SKU000001",
    "quantity": 3,
    "location": "online",
    "ttl": 300
  }'
```

**Response:**

```json
{
  "hold_id": "hold-a1b2c3d4",
  "sku": "SKU000001",
  "quantity": 3,
  "location": "online",
  "remaining_stock": 497,
  "expires_at": "2024-01-15T10:35:00",
  "status": "active"
}
```

**Error (Insufficient Stock):**

```json
{
  "detail": "Insufficient stock for SKU000001 at online"
}
```

#### 3. Release Hold

```bash
POST /release
```

**Request:**

```json
{
  "hold_id": "hold-a1b2c3d4"
}
```

**Example:**

```bash
curl -X POST http://localhost:8001/release \
  -H "Content-Type: application/json" \
  -d '{"hold_id": "hold-a1b2c3d4"}'
```

**Response:**

```json
{
  "hold_id": "hold-a1b2c3d4",
  "status": "released",
  "restored_stock": 500
}
```

#### 4. Simulate Sale (Demo)

```bash
POST /simulate/sale
```

**Request:**

```json
{
  "sku": "SKU000001",
  "quantity": 2,
  "location": "store:STORE_MUMBAI"
}
```

**Example:**

```bash
curl -X POST http://localhost:8001/simulate/sale \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "SKU000001",
    "quantity": 2,
    "location": "store:STORE_MUMBAI"
  }'
```

**Response:**

```json
{
  "sku": "SKU000001",
  "quantity_sold": 2,
  "location": "store:STORE_MUMBAI",
  "remaining_stock": 180,
  "status": "sold"
}
```

## 🏗️ Architecture

### Redis Key Structure

```
stock:{sku}:online                → int (online quantity)
stock:{sku}:store:{store_id}      → int (store quantity)
hold:{hold_id}                    → json (hold data) [TTL]
idemp:{key}                       → json (cached response) [1hr TTL]
holds_by_expiry                   → sorted set (hold_id → expiry_timestamp)
```

### Atomic Operations (Lua Scripts)

**Hold Stock:**

```lua
local key = 'stock:' .. sku .. ':' .. location
local current = tonumber(redis.call('GET', key) or 0)

if current >= quantity then
    redis.call('DECRBY', key, quantity)
    return current - quantity
else
    return -1
end
```

**Release Stock:**

```lua
local key = 'stock:' .. sku .. ':' .. location
redis.call('INCRBY', key, quantity)
return tonumber(redis.call('GET', key))
```

### Background Tasks

**Hold Cleanup (every 10 seconds):**

```python
expired_holds = get_expired_holds()  # ZRANGEBYSCORE holds_by_expiry -inf now
for hold_id in expired_holds:
    cleanup_expired_hold(hold_id)  # Delete hold, remove from sorted set
```

## 🧪 Testing

### Test Flow

```bash
# 1. Check inventory
curl http://localhost:8001/inventory/SKU000001

# 2. Create hold (decrements stock)
curl -X POST http://localhost:8001/hold \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU000001", "quantity": 5, "location": "online", "ttl": 60}'

# 3. Check inventory again (should be reduced)
curl http://localhost:8001/inventory/SKU000001

# 4. Release hold (restores stock)
curl -X POST http://localhost:8001/release \
  -H "Content-Type: application/json" \
  -d '{"hold_id": "hold-xxx"}'

# 5. Wait 60 seconds → hold auto-expires and stock restores
```

### Test Idempotency

```bash
# First request
curl -X POST http://localhost:8001/hold \
  -H "X-Idempotency-Key: test-123" \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU000001", "quantity": 1, "location": "online"}'

# Duplicate request (same key) → returns cached response
curl -X POST http://localhost:8001/hold \
  -H "X-Idempotency-Key: test-123" \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU000001", "quantity": 1, "location": "online"}'
```

### Test Concurrent Access

```bash
# Run in multiple terminals simultaneously
for i in {1..10}; do
  curl -X POST http://localhost:8001/hold \
    -H "Content-Type: application/json" \
    -d '{"sku": "SKU000001", "quantity": 1, "location": "online"}' &
done
wait

# Verify stock reduced by exactly 10 (atomic operations)
curl http://localhost:8001/inventory/SKU000001
```

## 📊 Redis Utils Reference

### Core Functions

```python
# Stock operations
get_stock(sku)                                  # Get all locations
set_stock(sku, qty, location)                   # Set quantity
hold_stock_atomic(sku, qty, location)           # Atomic decrement
release_stock_atomic(sku, qty, location)        # Atomic increment

# Hold management
create_hold(hold_id, hold_data, ttl)           # Create with expiry
get_hold(hold_id)                               # Retrieve hold
release_hold(hold_id)                           # Delete hold

# Idempotency
check_idempotency(key)                          # Check cache
save_idempotency(key, response, ttl=3600)      # Save response

# Expiry tracking
get_expired_holds()                             # ZRANGEBYSCORE query
cleanup_expired_hold(hold_id)                   # Delete + remove from sorted set
```

## 🔍 Monitoring

### Health Check

```bash
curl http://localhost:8001/health
```

**Response:**

```json
{
  "status": "healthy",
  "redis": "connected",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Logs

```bash
# Watch cleanup logs
✓ Cleaned up expired hold: hold-xyz123
✓ Cleaned up 3 expired holds
```

## 📝 Integration

### Sales Agent Integration

```python
import requests

# Check inventory before placing order
response = requests.get(f"http://localhost:8001/inventory/{sku}")
stock = response.json()

if stock["online_stock"] >= quantity:
    # Create hold
    hold_response = requests.post(
        "http://localhost:8001/hold",
        json={"sku": sku, "quantity": quantity, "location": "online", "ttl": 300},
        headers={"X-Idempotency-Key": f"order-{order_id}"}
    )
    hold_data = hold_response.json()
    
    # Process payment...
    
    if payment_success:
        # Hold auto-expires, stock already decremented
        pass
    else:
        # Release hold
        requests.post("http://localhost:8001/release", json={"hold_id": hold_data["hold_id"]})
```

## 🛠️ Troubleshooting

### Redis Connection Error

```bash
# Check .env file
cat ../../../.env | grep REDIS_URL

# Test connection
python -c "import redis_utils; print(redis_utils.check_redis_health())"
```

### Port Already in Use

```bash
# Change port in app.py
uvicorn.run("app:app", host="0.0.0.0", port=8002)
```

### CSV Files Not Found

```bash
# Verify data files exist
ls -la ../../../data/merged_products_902_rows.csv
ls -la ../../../data/inventory_realistic.csv
```

## 📂 File Structure

```
backend/agents/worker_agents/inventory/
├── app.py              # FastAPI server
├── redis_utils.py      # Redis operations + Lua scripts
├── seed_inventory.py   # CSV loader
└── README.md           # This file
```

## 🚦 Production Considerations

1. **Rate Limiting**: Add rate limiter middleware
2. **Authentication**: Require API keys for POST endpoints
3. **Monitoring**: Integrate APM (Datadog, New Relic)
4. **Scaling**: Use Redis Cluster for high throughput
5. **Backup**: Schedule Redis RDB snapshots
6. **Alerting**: Monitor hold expiry cleanup failures

## 📄 License

Part of EY_CodeCrafters retail sales platform.

---

**Last Updated:** 2024-01-15  
**Version:** 1.0.0  
**Redis Version:** 7.0+  
**Python Version:** 3.12+
