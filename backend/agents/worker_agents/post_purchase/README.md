# Post-Purchase Support Agent

Handles customer returns, exchanges, and complaints after order delivery.

## Main Endpoints

### 1. Process Return
```bash
POST /post-purchase/return
{
  "user_id": "user123",
  "order_id": "ORDER_001",
  "product_sku": "SKU000001",
  "reason_code": "SIZE_ISSUE",
  "additional_comments": "Too small"
}
```

### 2. Process Exchange
```bash
POST /post-purchase/exchange
{
  "user_id": "user123",
  "order_id": "ORDER_001",
  "product_sku": "SKU000001",
  "current_size": "M",
  "requested_size": "L"
}
```

### 3. Raise Complaint
```bash
POST /post-purchase/complaint
{
  "user_id": "user123",
  "order_id": "ORDER_001",
  "issue_type": "product_quality",
  "description": "Product not working properly",
  "priority": "high"
}
```

### 4. Get Return Reasons
```bash
GET /post-purchase/return-reasons
```

## Return Reasons Available

- SIZE_ISSUE - Size doesn't fit
- QUALITY_ISSUE - Quality issue / Defective
- WRONG_ITEM - Wrong item received
- NOT_AS_DESCRIBED - Not as described
- CHANGED_MIND - Changed my mind
- DUPLICATE_ORDER - Ordered by mistake
- FOUND_BETTER_PRICE - Found better price
- LATE_DELIVERY - Delivery too late
- DAMAGED_IN_SHIPPING - Damaged during shipping
- NOT_SATISFIED - Not satisfied

## Running

```bash
cd backend/agents/worker_agents/post_purchase
python app.py
```

Server: `http://localhost:8005`
