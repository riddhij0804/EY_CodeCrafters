/**
 * Sales Agent Service - Complete Frontend Integration
 * Implements the full workflow from the proposed solution:
 * 1. Discovery & conversational shopping
 * 2. Visual search for similar products
 * 3. Profile-based recommendations
 * 4. Gift suggestions
 * 5. Inventory verification before checkout
 * 6. Payment processing
 * 7. Post-purchase styling
 * 8. Fulfillment tracking
 * 9. Returns/exchanges
 */

import { API_ENDPOINTS, apiCall } from '../config/api';

export const salesAgentService = {
  /**
   * Step 1: Send message to sales agent with orchestration
   * Analyzes intent and coordinates with worker agents
   */
  sendMessage: async (message, sessionToken, userId, metadata = {}) => {
    try {
      const response = await fetch(API_ENDPOINTS.SEND_MESSAGE, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          session_token: sessionToken,
          user_id: userId,
          metadata
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Send message error:', error);
      throw error;
    }
  },

  /**
   * Step 2: Visual search - upload image to find similar products
   * Based on: "When Aisha uploads a jacket photo, system identifies visually similar product"
   */
  visualSearch: async (imageFile) => {
    try {
      const formData = new FormData();
      formData.append('image', imageFile);

      const response = await fetch(API_ENDPOINTS.VISUAL_SEARCH, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Visual search error:', error);
      return { status: 'error', results: [], error: error.message };
    }
  },

  /**
   * Step 3: Get personalized recommendations
   * Based on: "System analyzes preferences and presents curated outfit styles"
   */
  getRecommendations: async (userId, occasion = null, stylePreference = 'casual', budget = 'mid') => {
    try {
      const params = new URLSearchParams({
        user_id: userId,
        style_preference: stylePreference,
        budget: budget
      });

      if (occasion) {
        params.append('occasion', occasion);
      }

      const response = await fetch(`${API_ENDPOINTS.RECOMMENDATIONS}?${params}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get recommendations error:', error);
      return { status: 'error', recommendations: [], error: error.message };
    }
  },

  /**
   * Step 4: Get gift suggestions
   * Based on: "On detecting gifting intent, system creates tailored gift suggestions"
   */
  getGiftSuggestions: async (recipientAge, recipientGender, occasion, budget = 'mid') => {
    try {
      const params = new URLSearchParams({ budget });
      
      if (recipientAge) params.append('recipient_age', recipientAge);
      if (recipientGender) params.append('recipient_gender', recipientGender);
      if (occasion) params.append('occasion', occasion);

      const response = await fetch(`${API_ENDPOINTS.GIFT_SUGGESTIONS}?${params}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Gift suggestions error:', error);
      return { status: 'error', suggestions: [], error: error.message };
    }
  },

  /**
   * Step 5: Verify inventory before checkout
   * Based on: "Before checkout, all items verified for availability with low-stock alerts"
   */
  verifyInventory: async (items) => {
    try {
      const response = await fetch(API_ENDPOINTS.VERIFY_INVENTORY, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(items)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Verify inventory error:', error);
      return { 
        status: 'error', 
        all_available: false, 
        error: error.message 
      };
    }
  },

  /**
   * Step 6: Complete checkout with full orchestration
   * Coordinates: Inventory -> Payment -> Fulfillment -> Post-Purchase
   */
  processCheckout: async (customerId, items, paymentMethod, shippingAddress, sessionToken = null) => {
    try {
      const response = await fetch(API_ENDPOINTS.CHECKOUT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          customer_id: customerId,
          items,
          payment_method: paymentMethod,
          shipping_address: shippingAddress,
          session_token: sessionToken
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Checkout error:', error);
      return { 
        status: 'error', 
        error: error.message,
        message: 'Failed to process checkout'
      };
    }
  },

  /**
   * Step 7: Get seasonal trends
   * Based on: "System proactively highlights current seasonal trends"
   */
  getSeasonalTrends: async (season = null) => {
    try {
      const url = season 
        ? `${API_ENDPOINTS.SEASONAL_TRENDS}?season=${season}`
        : API_ENDPOINTS.SEASONAL_TRENDS;

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Seasonal trends error:', error);
      return { status: 'error', trends: [], error: error.message };
    }
  },

  /**
   * Get AI-powered outfit suggestions from the stylist agent
   * Triggered immediately after a successful purchase
   */
  getStylistSuggestions: async (payload) => {
    try {
      return await apiCall(API_ENDPOINTS.STYLIST_OUTFIT_SUGGESTIONS, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch (error) {
      console.error('Stylist suggestions error:', error);
      throw error;
    }
  },

  /**
   * Get products from CSV data
   */
  getProducts: async (filters = {}) => {
    try {
      const params = new URLSearchParams();
      
      if (filters.limit) params.append('limit', filters.limit);
      if (filters.category) params.append('category', filters.category);
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.min_price) params.append('min_price', filters.min_price);
      if (filters.max_price) params.append('max_price', filters.max_price);

      const url = `${API_ENDPOINTS.DATA_PRODUCTS}${params.toString() ? '?' + params : ''}`;
      return await apiCall(url);
    } catch (error) {
      console.error('Get products error:', error);
      return { total: 0, products: [] };
    }
  },

  /**
   * Get specific product by SKU
   */
  getProduct: async (sku) => {
    try {
      return await apiCall(`${API_ENDPOINTS.DATA_PRODUCTS}/${sku}`);
    } catch (error) {
      console.error('Get product error:', error);
      throw error;
    }
  },

  /**
   * Get customer data from CSV
   */
  getCustomer: async (customerId) => {
    try {
      return await apiCall(`${API_ENDPOINTS.DATA_CUSTOMERS}/${customerId}`);
    } catch (error) {
      console.error('Get customer error:', error);
      throw error;
    }
  },

  /**
   * Get orders from CSV
   */
  getOrders: async (customerId = null) => {
    try {
      const url = customerId 
        ? `${API_ENDPOINTS.DATA_ORDERS}?customer_id=${customerId}`
        : API_ENDPOINTS.DATA_ORDERS;
      
      return await apiCall(url);
    } catch (error) {
      console.error('Get orders error:', error);
      return { total: 0, orders: [] };
    }
  },

  /**
   * Session management
   */
  startSession: async (phone, channel = 'whatsapp') => {
    try {
      const response = await fetch(API_ENDPOINTS.SESSION_START, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ phone, channel })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Start session error:', error);
      throw error;
    }
  },

  endSession: async (sessionToken) => {
    try {
      const response = await fetch(API_ENDPOINTS.SESSION_END, {
        method: 'POST',
        headers: {
          'X-Session-Token': sessionToken,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('End session error:', error);
      throw error;
    }
  },

  /**
   * Helper: Complete shopping workflow
   * Combines multiple steps for a seamless experience
   */
  completeShoppingFlow: async (userId, message, sessionToken, context = {}) => {
    const workflow = {
      message_response: null,
      recommendations: null,
      seasonal_trends: null,
      products: null
    };

    try {
      // Step 1: Send message and get intent-based response
      workflow.message_response = await salesAgentService.sendMessage(
        message, 
        sessionToken, 
        userId, 
        context
      );

      // Step 2: If recommendations are included, great! Otherwise fetch separately
      if (!workflow.message_response.metadata?.recommendations?.length) {
        const recsResponse = await salesAgentService.getRecommendations(userId);
        workflow.recommendations = recsResponse.recommendations || [];
      } else {
        workflow.recommendations = workflow.message_response.metadata.recommendations;
      }

      // Step 3: Get seasonal trends proactively
      const trendsResponse = await salesAgentService.getSeasonalTrends();
      workflow.seasonal_trends = trendsResponse.trends || [];

      // Step 4: Get some general products from CSV
      const productsResponse = await salesAgentService.getProducts({ limit: 10 });
      workflow.products = productsResponse.products || [];

      return {
        status: 'success',
        workflow
      };

    } catch (error) {
      console.error('Shopping flow error:', error);
      return {
        status: 'error',
        error: error.message,
        workflow
      };
    }
  }
};

export default salesAgentService;
