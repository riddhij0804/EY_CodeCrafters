// Loyalty Service - Handles loyalty points, coupons, and promotions

import { API_ENDPOINTS, apiCall } from '../config/api';

/**
 * Get loyalty points for a user
 * @param {string} userId - User ID
 * @returns {Promise<Object>} Points balance
 */
export const getLoyaltyPoints = async (userId) => {
  return apiCall(`${API_ENDPOINTS.LOYALTY_POINTS}/${userId}`);
};

/**
 * Apply loyalty benefits (points + coupons)
 * @param {Object} loyaltyData - Loyalty application data
 * @param {string} loyaltyData.user_id - User ID
 * @param {number} loyaltyData.cart_total - Cart total amount
 * @param {string} loyaltyData.applied_coupon - Coupon code (optional)
 * @param {number} loyaltyData.loyalty_points_used - Points to redeem
 * @returns {Promise<Object>} Discount details
 */
export const applyLoyalty = async (loyaltyData) => {
  return apiCall(API_ENDPOINTS.LOYALTY_APPLY, {
    method: 'POST',
    body: JSON.stringify(loyaltyData),
  });
};

/**
 * Add points to user account
 * @param {Object} pointsData - Points data
 * @param {string} pointsData.user_id - User ID
 * @param {number} pointsData.points - Points to add
 * @param {string} pointsData.reason - Reason for adding points
 * @returns {Promise<Object>} Updated points balance
 */
export const addLoyaltyPoints = async (pointsData) => {
  return apiCall(API_ENDPOINTS.LOYALTY_ADD_POINTS, {
    method: 'POST',
    body: JSON.stringify(pointsData),
  });
};

/**
 * Validate a coupon code
 * @param {string} couponCode - Coupon code to validate
 * @returns {Promise<Object>} Coupon validation result
 */
export const validateCoupon = async (couponCode) => {
  return apiCall(`${API_ENDPOINTS.LOYALTY_VALIDATE_COUPON}/${couponCode}`);
};

/**
 * Get user's tier information
 * @param {string} userId - User ID
 * @returns {Promise<Object>} Tier details
 */
export const getTierInfo = async (userId) => {
  return apiCall(`${API_ENDPOINTS.LOYALTY_TIER_INFO}/${userId}`);
};

/**
 * Get available promotions
 * @param {Object} promotionData - Promotion query data
 * @param {string} promotionData.user_id - User ID
 * @param {number} promotionData.cart_total - Cart total
 * @param {string} promotionData.category - Product category (optional)
 * @returns {Promise<Object>} Available promotions
 */
export const getAvailablePromotions = async (promotionData) => {
  return apiCall(API_ENDPOINTS.LOYALTY_PROMOTIONS, {
    method: 'POST',
    body: JSON.stringify(promotionData),
  });
};

export default {
  getLoyaltyPoints,
  applyLoyalty,
  addLoyaltyPoints,
  validateCoupon,
  getTierInfo,
  getAvailablePromotions,
};
