// Post-Purchase Service - Handles returns, exchanges, and complaints

import { API_ENDPOINTS, apiCall } from '../config/api';

/**
 * Get return reasons
 * @returns {Promise<Object>} List of return reasons
 */
export const getReturnReasons = async () => {
  return apiCall(API_ENDPOINTS.POST_PURCHASE_RETURN_REASONS);
};

/**
 * Get issue types for complaints
 * @returns {Promise<Object>} List of issue types
 */
export const getIssueTypes = async () => {
  return apiCall(API_ENDPOINTS.POST_PURCHASE_ISSUE_TYPES);
};

/**
 * Initiate a return request
 * @param {Object} returnData - Return request data
 * @param {string} returnData.user_id - User ID
 * @param {string} returnData.order_id - Order ID
 * @param {string} returnData.product_sku - Product SKU
 * @param {string} returnData.reason_code - Return reason code
 * @param {string} returnData.additional_comments - Additional comments (optional)
 * @param {Array<string>} returnData.images - Image URLs (optional)
 * @returns {Promise<Object>} Return response with return_id
 */
export const initiateReturn = async (returnData) => {
  return apiCall(API_ENDPOINTS.POST_PURCHASE_RETURN, {
    method: 'POST',
    body: JSON.stringify(returnData),
  });
};

/**
 * Initiate an exchange request
 * @param {Object} exchangeData - Exchange request data
 * @param {string} exchangeData.user_id - User ID
 * @param {string} exchangeData.order_id - Order ID
 * @param {string} exchangeData.product_sku - Product SKU to exchange
 * @param {string} exchangeData.current_size - Current size
 * @param {string} exchangeData.requested_size - Requested new size
 * @param {string} exchangeData.reason - Reason for exchange (optional)
 * @returns {Promise<Object>} Exchange response with exchange_id
 */
export const initiateExchange = async (exchangeData) => {
  return apiCall(API_ENDPOINTS.POST_PURCHASE_EXCHANGE, {
    method: 'POST',
    body: JSON.stringify(exchangeData),
  });
};

/**
 * Raise a complaint
 * @param {Object} complaintData - Complaint data
 * @param {string} complaintData.user_id - User ID
 * @param {string} complaintData.order_id - Order ID (optional)
 * @param {string} complaintData.issue_type - Issue type
 * @param {string} complaintData.description - Issue description
 * @param {string} complaintData.priority - Priority (low, medium, high)
 * @returns {Promise<Object>} Complaint response with complaint_id
 */
export const raiseComplaint = async (complaintData) => {
  return apiCall(API_ENDPOINTS.POST_PURCHASE_COMPLAINT, {
    method: 'POST',
    body: JSON.stringify(complaintData),
  });
};

/**
 * Get user's returns history
 * @param {string} userId - User ID
 * @returns {Promise<Object>} List of returns
 */
export const getUserReturns = async (userId) => {
  return apiCall(`${API_ENDPOINTS.POST_PURCHASE_RETURNS}/${userId}`);
};

/**
 * Get Groq AI outfit suggestions for a purchased product
 * @param {Object} payload - Outfit request payload
 * @returns {Promise<Object>} Styling recommendations
 */
/**
 * Submit post-purchase feedback
 * @param {Object} payload - Feedback payload
 * @returns {Promise<Object>} Feedback acknowledgement
 */
export const submitFeedback = async (payload) => {
  return apiCall(API_ENDPOINTS.POST_PURCHASE_FEEDBACK, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
};

/**
 * Register a freshly completed order so post-purchase flows can reference it
 * @param {Object} payload - Order payload captured after payment
 * @returns {Promise<Object>} Stored order details
 */
export const registerPostPurchaseOrder = async (payload) => {
  return apiCall(API_ENDPOINTS.POST_PURCHASE_REGISTER_ORDER, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
};

export default {
  getReturnReasons,
  getIssueTypes,
  initiateReturn,
  initiateExchange,
  raiseComplaint,
  getUserReturns,
  submitFeedback,
  registerPostPurchaseOrder,
};
