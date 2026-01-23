/**
 * Data Service - Handles all CSV data endpoints
 * Products, Customers, Orders, Stores, Inventory, Payments
 */

import { apiCall } from '../config/api';

const DATA_SERVICE = 'http://localhost:8007';

export const dataService = {
  /**
   * Get products with optional filters
   */
  getProducts: async (params = {}) => {
    const queryParams = new URLSearchParams();
    
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.category) queryParams.append('category', params.category);
    if (params.brand) queryParams.append('brand', params.brand);
    if (params.min_price) queryParams.append('min_price', params.min_price);
    if (params.max_price) queryParams.append('max_price', params.max_price);
    
    const url = `${DATA_SERVICE}/products${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return await apiCall(url);
  },

  /**
   * Get specific product by SKU
   */
  getProduct: async (sku) => {
    return await apiCall(`${DATA_SERVICE}/products/${sku}`);
  },

  /**
   * Get customers
   */
  getCustomers: async (limit = 20) => {
    return await apiCall(`${DATA_SERVICE}/customers?limit=${limit}`);
  },

  /**
   * Get specific customer
   */
  getCustomer: async (customerId) => {
    return await apiCall(`${DATA_SERVICE}/customers/${customerId}`);
  },

  /**
   * Get orders with optional filters
   */
  getOrders: async (params = {}) => {
    const queryParams = new URLSearchParams();
    
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.customer_id) queryParams.append('customer_id', params.customer_id);
    if (params.status) queryParams.append('status', params.status);
    
    const url = `${DATA_SERVICE}/orders${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return await apiCall(url);
  },

  /**
   * Get specific order
   */
  getOrder: async (orderId) => {
    return await apiCall(`${DATA_SERVICE}/orders/${orderId}`);
  },

  /**
   * Get all stores
   */
  getStores: async () => {
    return await apiCall(`${DATA_SERVICE}/stores`);
  },

  /**
   * Get inventory data
   */
  getInventory: async (limit = 20) => {
    return await apiCall(`${DATA_SERVICE}/inventory?limit=${limit}`);
  },

  /**
   * Get payment records
   */
  getPayments: async (limit = 20) => {
    return await apiCall(`${DATA_SERVICE}/payments?limit=${limit}`);
  },

  /**
   * Search products by name
   */
  searchProducts: async (searchTerm, limit = 10) => {
    const data = await dataService.getProducts({ limit: 100 });
    const filtered = data.products.filter(p => 
      p.ProductDisplayName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.brand?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.category?.toLowerCase().includes(searchTerm.toLowerCase())
    );
    return {
      total: filtered.length,
      products: filtered.slice(0, limit)
    };
  }
};

export default dataService;
