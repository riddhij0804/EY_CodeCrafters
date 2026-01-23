# Payment Agent

Processes payments via UPI, Card, Wallet, and POS terminals with authorization/capture support.

## Main Endpoints

### Process Payment
```bash
POST /payment/process
{
  "user_id": "user123",
  "amount": 1350.0,
  "payment_method": "upi",
  "order_id": "ORDER123"
}
```

### Authorize & Capture Payment
```bash
POST /payment/authorize
POST /payment/capture
```

## Running

```bash
cd backend/agents/worker_agents/payment
python app.py
```

Server: `http://localhost:8003`

## Razorpay Test Flow

1. Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` to `backend/.env` (test mode values).
2. Create a test order:
   ```bash
   curl -X POST http://localhost:8003/payment/razorpay/create-order \
     -H "Content-Type: application/json" \
     -d '{"amount_rupees": 499}'
   ```
3. Use the returned `order.id` and `razorpay_key_id` with Razorpay Checkout on the frontend.
4. Record the test payment after checkout:
   ```bash
   curl -X POST http://localhost:8003/payment/razorpay/verify-payment \
     -H "Content-Type: application/json" \
     -d '{"razorpay_payment_id": "pay_123", "razorpay_order_id": "order_123"}'
   ```
5. The payment entry is appended to `backend/data/payments.csv` and a transaction record is stored in Redis when configured.
