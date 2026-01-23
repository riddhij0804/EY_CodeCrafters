# Backend Integration Guide

## ✅ Integration Status

### Phase 1: Service Layer - COMPLETE
All backend services have been integrated into the frontend with proper API configuration and service layers.

---

## 📁 File Structure

```
frontend/src/
├── config/
│   └── api.js                    # ✅ API endpoints configuration
├── services/
│   ├── index.js                  # ✅ Service exports
│   ├── inventoryService.js       # ✅ Inventory operations
│   ├── loyaltyService.js         # ✅ Loyalty & coupons
│   ├── paymentService.js         # ✅ Payment processing
│   ├── postPurchaseService.js    # ✅ Returns & exchanges
│   └── fulfillmentService.js     # ✅ Order fulfillment
└── components/
    ├── Chat.jsx                   # ✅ Session management integrated
    └── KioskChat.jsx              # ⏳ Ready for integration
```

---

## 🔌 Backend Services & Ports

| Service | Port | Status | Endpoints |
|---------|------|--------|-----------|
| **Sales Agent** | 8000 | ✅ Integrated | Session management, messaging |
| **Inventory** | 8001 | ✅ Ready | Check stock, hold, release |
| **Loyalty** | 8002 | ✅ Ready | Points, coupons, promotions |
| **Payment** | 8003 | ✅ Ready | Process payments, refunds |
| **Fulfillment** | 8004 | ✅ Ready | Order tracking, delivery |
| **Post-Purchase** | 8005 | ✅ Ready | Returns, exchanges, complaints |
| **Stylist** | 8006 | ⏳ Pending | Style recommendations |

---

## 🚀 How to Use Services

### 1. Import Services
```javascript
import { 
  inventoryService, 
  loyaltyService, 
  paymentService,
  postPurchaseService,
  fulfillmentService
} from '../services';
```

### 2. Use in Components

#### **Check Inventory**
```javascript
const checkStock = async (sku) => {
  try {
    const stock = await inventoryService.getInventory(sku);
    console.log('Stock:', stock);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

#### **Get Loyalty Points**
```javascript
const getPoints = async (userId) => {
  try {
    const points = await loyaltyService.getLoyaltyPoints(userId);
    console.log('Points:', points);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

#### **Process Payment**
```javascript
const makePayment = async (paymentData) => {
  try {
    const result = await paymentService.processPayment({
      user_id: 'user123',
      amount: 2999,
      payment_method: 'upi',
      order_id: 'ORD123'
    });
    console.log('Payment:', result);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

#### **Initiate Return**
```javascript
const returnProduct = async (returnData) => {
  try {
    const result = await postPurchaseService.initiateReturn({
      user_id: 'user123',
      order_id: 'ORD123',
      product_sku: 'SKU123',
      reason_code: 'SIZE_ISSUE',
      additional_comments: 'Too small'
    });
    console.log('Return:', result);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

#### **Track Order**
```javascript
const trackOrder = async (orderId) => {
  try {
    const status = await fulfillmentService.getFulfillmentStatus(orderId);
    console.log('Order Status:', status);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

---

## 🔥 Complete Purchase Flow Example

```javascript
const completePurchaseFlow = async () => {
  try {
    // 1. Check Inventory
    const stock = await inventoryService.getInventory('SKU123');
    if (stock.total_stock < 1) {
      alert('Out of stock!');
      return;
    }

    // 2. Hold Inventory
    const hold = await inventoryService.holdInventory({
      sku: 'SKU123',
      quantity: 1,
      location: 'online',
      ttl: 300
    });

    // 3. Apply Loyalty
    const loyalty = await loyaltyService.applyLoyalty({
      user_id: 'user123',
      cart_total: 2999,
      applied_coupon: 'SAVE20',
      loyalty_points_used: 100
    });

    // 4. Process Payment
    const payment = await paymentService.processPayment({
      user_id: 'user123',
      amount: loyalty.final_total,
      payment_method: 'upi',
      order_id: 'ORD123'
    });

    // 5. Start Fulfillment
    const fulfillment = await fulfillmentService.startFulfillment({
      order_id: 'ORD123',
      inventory_status: 'RESERVED',
      payment_status: 'SUCCESS',
      amount: loyalty.final_total,
      inventory_hold_id: hold.hold_id,
      payment_transaction_id: payment.transaction_id
    });

    alert('Order placed successfully!');
    
  } catch (error) {
    console.error('Purchase failed:', error);
    alert('Purchase failed: ' + error.message);
  }
};
```

---

## ⚠️ Error Handling

All services use the centralized `apiCall` function with built-in error handling:

```javascript
try {
  const result = await someService.someMethod();
  // Handle success
} catch (error) {
  // Error is automatically logged
  // Display user-friendly message
  console.error(error.message);
}
```

---

## 🧪 Testing Services

### Start All Backend Services:

```bash
# Terminal 1 - Inventory
cd backend/agents/worker_agents/inventory
python app.py

# Terminal 2 - Loyalty
cd backend/agents/worker_agents/loyalty
python app.py

# Terminal 3 - Payment
cd backend/agents/worker_agents/payment
python app.py

# Terminal 4 - Fulfillment
cd backend/agents/worker_agents/fulfillment
python app.py

# Terminal 5 - Post-Purchase
cd backend/agents/worker_agents/post_purchase
python app.py
```

### Start Frontend:
```bash
cd frontend
npm run dev
```

---

## 📋 Next Steps

### Phase 2: UI Integration (In Progress)
- [ ] Add product search/display UI
- [ ] Add shopping cart component
- [ ] Add checkout flow UI
- [ ] Add order tracking UI
- [ ] Add returns/exchanges UI
- [ ] Add loyalty points display
- [ ] Add payment method selector

### Phase 3: Real-time Features
- [ ] WebSocket for live updates
- [ ] Push notifications
- [ ] Live chat with agents

---

## 🎯 Quick Reference

### Common Operations

| Operation | Service | Method |
|-----------|---------|--------|
| Check stock | Inventory | `getInventory(sku)` |
| Hold stock | Inventory | `holdInventory(data)` |
| Get points | Loyalty | `getLoyaltyPoints(userId)` |
| Apply coupon | Loyalty | `validateCoupon(code)` |
| Pay | Payment | `processPayment(data)` |
| Track order | Fulfillment | `getFulfillmentStatus(orderId)` |
| Return | Post-Purchase | `initiateReturn(data)` |
| Exchange | Post-Purchase | `initiateExchange(data)` |

---

## 📞 Support

For issues or questions, check:
1. Browser console for errors
2. Backend terminal logs
3. Network tab in DevTools
4. API documentation at `http://localhost:PORT/docs`

---

**Status:** ✅ Service layer complete, ready for UI integration
**Last Updated:** December 17, 2025
