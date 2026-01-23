// Inventory Service - Handles product inventory operations

import { API_ENDPOINTS, apiCall } from '../config/api';

/**
 * Get inventory details for a product
 * @param {string} sku - Product SKU
 * @returns {Promise<Object>} Inventory details
 */
export const getInventory = async (sku) => {
  return apiCall(`${API_ENDPOINTS.INVENTORY_CHECK}/${sku}`);
};

/**
 * Hold inventory for a product
 * @param {Object} holdData - Hold request data
 * @param {string} holdData.sku - Product SKU
 * @param {number} holdData.quantity - Quantity to hold
 * @param {string} holdData.location - Location (online or store:store_id)
 * @param {number} holdData.ttl - Hold duration in seconds (default 300)
 * @returns {Promise<Object>} Hold response with hold_id
 */
export const holdInventory = async (holdData) => {
  return apiCall(API_ENDPOINTS.INVENTORY_HOLD, {
    method: 'POST',
    body: JSON.stringify(holdData),
  });
};

/**
 * Release a held inventory
 * @param {string} holdId - Hold ID to release
 * @returns {Promise<Object>} Release response
 */
export const releaseInventory = async (holdId) => {
  return apiCall(API_ENDPOINTS.INVENTORY_RELEASE, {
    method: 'POST',
    body: JSON.stringify({ hold_id: holdId }),
  });
};

/**
 * Simulate a sale (reduce inventory)
 * @param {Object} saleData - Sale data
 * @param {string} saleData.sku - Product SKU
 * @param {number} saleData.quantity - Quantity sold
 * @param {string} saleData.location - Location
 * @returns {Promise<Object>} Sale response
 */
export const simulateSale = async (saleData) => {
  return apiCall(API_ENDPOINTS.INVENTORY_SIMULATE_SALE, {
    method: 'POST',
    body: JSON.stringify(saleData),
  });
};

export default {
  getInventory,
  holdInventory,
  releaseInventory,
  simulateSale,
};
