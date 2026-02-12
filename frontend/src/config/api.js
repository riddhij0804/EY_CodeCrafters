// API Configuration for all backend services

const API_BASE_URL = 'http://localhost';

export const API_ENDPOINTS = {
  // Session Management (Port 8000)
  SESSION_MANAGER: `${API_BASE_URL}:8000`,
  SESSION_START: `${API_BASE_URL}:8000/session/start`,
  SESSION_END: `${API_BASE_URL}:8000/session/end`,
  SESSION_UPDATE: `${API_BASE_URL}:8000/session/update`,
  SESSION_LOGIN: `${API_BASE_URL}:8000/session/login`,
  
  // Authentication (Password-based - Port 8000)
  AUTH_SIGNUP: `${API_BASE_URL}:8000/auth/signup`,
  AUTH_LOGIN: `${API_BASE_URL}:8000/auth/login`,
  AUTH_LOGOUT: `${API_BASE_URL}:8000/auth/logout`,
  AUTH_QR_INIT: `${API_BASE_URL}:8000/auth/qr-init`,
  AUTH_QR_VERIFY: `${API_BASE_URL}:8000/auth/qr-verify`,
  
  // Sales Agent with Orchestration (Port 8010)
  SALES_AGENT: `${API_BASE_URL}:8010`,
  SEND_MESSAGE: `${API_BASE_URL}:8010/api/message`,
  RESUME_SESSION: `${API_BASE_URL}:8010/api/resume_session`,
  VISUAL_SEARCH: `${API_BASE_URL}:8010/api/visual-search`,
  RECOMMENDATIONS: `${API_BASE_URL}:8010/api/recommendations`,
  GIFT_SUGGESTIONS: `${API_BASE_URL}:8010/api/gift-suggestions`,
  CHECKOUT: `${API_BASE_URL}:8010/api/checkout`,
  POST_PAYMENT: `${API_BASE_URL}:8010/api/post-payment`,
  VERIFY_INVENTORY: `${API_BASE_URL}:8010/api/verify-inventory`,
  SEASONAL_TRENDS: `${API_BASE_URL}:8010/api/seasonal-trends`,

  // Inventory Agent
  INVENTORY: `${API_BASE_URL}:8001`,
  INVENTORY_CHECK: `${API_BASE_URL}:8001/inventory`,
  INVENTORY_HOLD: `${API_BASE_URL}:8001/hold`,
  INVENTORY_RELEASE: `${API_BASE_URL}:8001/release`,
  INVENTORY_SIMULATE_SALE: `${API_BASE_URL}:8001/simulate/sale`,

  // Loyalty Agent
  LOYALTY: `${API_BASE_URL}:8002`,
  LOYALTY_POINTS: `${API_BASE_URL}:8002/loyalty/points`,
  LOYALTY_TIER_INFO: `${API_BASE_URL}:8002/loyalty/tier`,
  LOYALTY_APPLY: `${API_BASE_URL}:8002/loyalty/apply`,
  LOYALTY_ADD_POINTS: `${API_BASE_URL}:8002/loyalty/add-points`,
  LOYALTY_VALIDATE_COUPON: `${API_BASE_URL}:8002/loyalty/validate-coupon`,
  LOYALTY_PROMOTIONS: `${API_BASE_URL}:8002/loyalty/available-promotions`,

  // Payment Agent
  PAYMENT: `${API_BASE_URL}:8003`,
  PAYMENT_PROCESS: `${API_BASE_URL}:8003/payment/process`,
  PAYMENT_TRANSACTION: `${API_BASE_URL}:8003/payment/transaction`,
  PAYMENT_USER_TRANSACTIONS: `${API_BASE_URL}:8003/payment/user-transactions`,
  PAYMENT_METHODS: `${API_BASE_URL}:8003/payment/methods`,
  PAYMENT_REFUND: `${API_BASE_URL}:8003/payment/refund`,
  PAYMENT_AUTHORIZE: `${API_BASE_URL}:8003/payment/authorize`,
  PAYMENT_CAPTURE: `${API_BASE_URL}:8003/payment/capture`,
    PAYMENT_NEXT_ORDER_ID: `${API_BASE_URL}:8003/payment/next-order-id`,
  PAYMENT_RAZORPAY_CREATE: `${API_BASE_URL}:8003/payment/razorpay/create-order`,
  PAYMENT_RAZORPAY_VERIFY: `${API_BASE_URL}:8003/payment/razorpay/verify-payment`,

  // Fulfillment Agent
  FULFILLMENT: `${API_BASE_URL}:8004`,
  FULFILLMENT_START: `${API_BASE_URL}:8004/fulfillment/start`,
  FULFILLMENT_STATUS: `${API_BASE_URL}:8004/fulfillment`,
  FULFILLMENT_UPDATE: `${API_BASE_URL}:8004/fulfillment/update-status`,
  FULFILLMENT_DELIVERED: `${API_BASE_URL}:8004/fulfillment/mark-delivered`,
  FULFILLMENT_CANCEL: `${API_BASE_URL}:8004/fulfillment/cancel-order`,
  FULFILLMENT_SET_DELIVERY_WINDOW: `${API_BASE_URL}:8004/fulfillment/set-delivery-window`,

  // Post-Purchase Agent
  POST_PURCHASE: `${API_BASE_URL}:8005`,
  POST_PURCHASE_RETURN: `${API_BASE_URL}:8005/post-purchase/return`,
  POST_PURCHASE_EXCHANGE: `${API_BASE_URL}:8005/post-purchase/exchange`,
  POST_PURCHASE_COMPLAINT: `${API_BASE_URL}:8005/post-purchase/complaint`,
  POST_PURCHASE_FEEDBACK: `${API_BASE_URL}:8005/post-purchase/feedback`,
  POST_PURCHASE_RETURN_REASONS: `${API_BASE_URL}:8005/post-purchase/return-reasons`,
  POST_PURCHASE_RETURNS: `${API_BASE_URL}:8005/post-purchase/returns`,
  POST_PURCHASE_ISSUE_TYPES: `${API_BASE_URL}:8005/post-purchase/issue-types`,
  POST_PURCHASE_REGISTER_ORDER: `${API_BASE_URL}:8005/post-purchase/register-order`,

  // Stylist Agent
  STYLIST: `${API_BASE_URL}:8006`,
  STYLIST_OUTFIT_SUGGESTIONS: `${API_BASE_URL}:8006/stylist/outfit-suggestions`,
  STYLIST_CARE_INSTRUCTIONS: `${API_BASE_URL}:8006/stylist/care-instructions`,
  STYLIST_OCCASION: `${API_BASE_URL}:8006/stylist/occasion-styling`,
  STYLIST_SEASONAL: `${API_BASE_URL}:8006/stylist/seasonal-styling`,
  STYLIST_FIT_FEEDBACK: `${API_BASE_URL}:8006/stylist/fit-feedback`,
  
  // Data API (CSV Data + Supabase Products)
  DATA_API: `${API_BASE_URL}:8007`,
  DATA_PRODUCTS: `${API_BASE_URL}:8007/products`,
  DATA_CUSTOMERS: `${API_BASE_URL}:8007/customers`,
  DATA_ORDERS: `${API_BASE_URL}:8007/orders`,
  DATA_STORES: `${API_BASE_URL}:8007/stores`,
  DATA_INVENTORY: `${API_BASE_URL}:8007/inventory`,
  DATA_PAYMENTS: `${API_BASE_URL}:8007/payments`,
  
  // Recommendation Agent
  RECOMMENDATION: `${API_BASE_URL}:8008`,
  RECOMMENDATION_PERSONALIZED: `${API_BASE_URL}:8008/recommend`,
  
  // Virtual Circles (Community Chat)
  VIRTUAL_CIRCLES: `${API_BASE_URL}:8007`
};

// Helper function for API calls with error handling
export const apiCall = async (url, options = {}) => {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      const msg = (errorBody && (errorBody.message || errorBody.error)) || `HTTP ${response.status}`;
      const err = new Error(msg);
      err.status = response.status;
      err.body = errorBody;
      throw err;
    }

    return await response.json();
  } catch (error) {
    console.error(`API call failed for ${url}:`, error);
    throw error;
  }
};

export default API_ENDPOINTS;
