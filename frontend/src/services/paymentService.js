// Payment Service - Handles payment processing and transactions

import { API_ENDPOINTS, apiCall } from '../config/api';

/**
 * Process a payment
 * @param {Object} paymentData - Payment data
 * @param {string} paymentData.user_id - User ID
 * @param {number} paymentData.amount - Payment amount
 * @param {string} paymentData.payment_method - Payment method (upi, card, wallet, netbanking, cod)
 * @param {string} paymentData.order_id - Order ID (optional)
 * @param {Object} paymentData.metadata - Additional metadata
 * @returns {Promise<Object>} Payment response with transaction_id
 */
export const processPayment = async (paymentData) => {
  return apiCall(API_ENDPOINTS.PAYMENT_PROCESS, {
    method: 'POST',
    body: JSON.stringify(paymentData),
  });
};

/**
 * Get transaction details
 * @param {string} transactionId - Transaction ID
 * @returns {Promise<Object>} Transaction details
 */
export const getTransaction = async (transactionId) => {
  return apiCall(`${API_ENDPOINTS.PAYMENT_TRANSACTION}/${transactionId}`);
};

/**
 * Get user's transaction history
 * @param {string} userId - User ID
 * @returns {Promise<Object>} List of transactions
 */
export const getUserTransactions = async (userId) => {
  return apiCall(`${API_ENDPOINTS.PAYMENT_USER_TRANSACTIONS}/${userId}`);
};

/**
 * Get supported payment methods
 * @returns {Promise<Object>} List of payment methods
 */
export const getPaymentMethods = async () => {
  return apiCall(API_ENDPOINTS.PAYMENT_METHODS);
};

/**
 * Process a refund
 * @param {Object} refundData - Refund data
 * @param {string} refundData.transaction_id - Transaction ID to refund
 * @param {number} refundData.amount - Refund amount (optional, full refund if not specified)
 * @param {string} refundData.reason - Refund reason
 * @returns {Promise<Object>} Refund response
 */
export const processRefund = async (refundData) => {
  return apiCall(API_ENDPOINTS.PAYMENT_REFUND, {
    method: 'POST',
    body: JSON.stringify(refundData),
  });
};

/**
 * Authorize a payment (hold funds)
 * @param {Object} authData - Authorization data
 * @param {string} authData.user_id - User ID
 * @param {number} authData.amount - Amount to authorize
 * @param {string} authData.payment_method - Payment method
 * @param {string} authData.order_id - Order ID
 * @returns {Promise<Object>} Authorization response
 */
export const authorizePayment = async (authData) => {
  return apiCall(API_ENDPOINTS.PAYMENT_AUTHORIZE, {
    method: 'POST',
    body: JSON.stringify(authData),
  });
};

/**
 * Capture an authorized payment
 * @param {Object} captureData - Capture data
 * @param {string} captureData.authorization_id - Authorization ID
 * @param {number} captureData.amount - Amount to capture (optional)
 * @returns {Promise<Object>} Capture response
 */
export const capturePayment = async (captureData) => {
  return apiCall(API_ENDPOINTS.PAYMENT_CAPTURE, {
    method: 'POST',
    body: JSON.stringify(captureData),
  });
};

/**
 * Create a Razorpay test order
 * @param {Object} orderData - Order payload
 * @param {number} orderData.amount_rupees - Amount in rupees
 * @param {string} [orderData.currency] - Currency code (default INR)
 * @param {string} [orderData.receipt] - Optional receipt identifier
 * @param {Object} [orderData.notes] - Additional metadata forwarded to Razorpay
 * @returns {Promise<Object>} Razorpay order details and key id
 */
export const createRazorpayOrder = async (orderData) => {
  return apiCall(API_ENDPOINTS.PAYMENT_RAZORPAY_CREATE, {
    method: 'POST',
    body: JSON.stringify(orderData),
  });
};

/**
 * Verify a Razorpay payment after checkout success
 * @param {Object} verificationData - Razorpay verification payload
 * @returns {Promise<Object>} Verification response from backend
 */
export const verifyRazorpayPayment = async (verificationData) => {
  return apiCall(API_ENDPOINTS.PAYMENT_RAZORPAY_VERIFY, {
    method: 'POST',
    body: JSON.stringify(verificationData),
  });
};

export default {
  processPayment,
  getTransaction,
  getUserTransactions,
  getPaymentMethods,
  processRefund,
  authorizePayment,
  capturePayment,
  createRazorpayOrder,
  verifyRazorpayPayment,
};
