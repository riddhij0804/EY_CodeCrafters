/**
 * Complete Shopping Workflow Component
 * Implements the full flow from the proposed solution image
 */

import { useState, useEffect } from 'react';
import { salesAgentService } from '../services';
import { ShoppingBag, Upload, Gift, TrendingUp, CheckCircle, Truck, Package } from 'lucide-react';

const ShoppingWorkflow = () => {
  const [step, setStep] = useState('discovery');
  const [userId] = useState('CUST001');
  const [cart, setCart] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [giftSuggestions, setGiftSuggestions] = useState([]);
  const [seasonalTrends, setSeasonalTrends] = useState([]);
  const [inventoryStatus, setInventoryStatus] = useState(null);
  const [orderStatus, setOrderStatus] = useState(null);

  // Step 1: Discovery & Recommendations
  const handleDiscovery = async (occasion = 'weekend_trip') => {
    try {
      const response = await salesAgentService.getRecommendations(userId, occasion);
      if (response.recommendations) {
        setRecommendations(response.recommendations);
        setStep('browsing');
      }
    } catch (error) {
      console.error('Discovery error:', error);
    }
  };

  // Step 2: Visual Search
  const handleVisualSearch = async (imageFile) => {
    try {
      const response = await salesAgentService.visualSearch(imageFile);
      if (response.results) {
        setRecommendations(response.results);
      }
    } catch (error) {
      console.error('Visual search error:', error);
    }
  };

  // Step 3: Add to Cart
  const addToCart = (product) => {
    const cartItem = {
      sku: product.sku,
      name: product.ProductDisplayName || product.name,
      price: product.price,
      quantity: 1,
      category: product.category,
      brand: product.brand
    };
    setCart([...cart, cartItem]);
  };

  // Step 4: Get Gift Suggestions
  const handleGiftMode = async () => {
    try {
      const response = await salesAgentService.getGiftSuggestions(25, 'female', 'birthday', 'mid');
      if (response.suggestions) {
        setGiftSuggestions(response.suggestions);
      }
    } catch (error) {
      console.error('Gift suggestions error:', error);
    }
  };

  // Step 5: Verify Inventory Before Checkout
  const verifyInventory = async () => {
    try {
      const response = await salesAgentService.verifyInventory(cart);
      setInventoryStatus(response);
      
      if (response.all_available) {
        setStep('payment');
      }
    } catch (error) {
      console.error('Inventory verification error:', error);
    }
  };

  // Step 6: Complete Checkout
  const completeCheckout = async () => {
    try {
      const response = await salesAgentService.processCheckout(
        userId,
        cart,
        { type: 'credit_card', card_number: '**** **** **** 1234' },
        { address: '123 Main St', city: 'Mumbai', zip: '400001' }
      );
      
      if (response.status === 'completed') {
        setOrderStatus(response);
        setStep('completed');
      }
    } catch (error) {
      console.error('Checkout error:', error);
    }
  };

  // Load seasonal trends on mount
  useEffect(() => {
    const loadTrends = async () => {
      const response = await salesAgentService.getSeasonalTrends();
      if (response.trends) {
        setSeasonalTrends(response.trends);
      }
    };
    loadTrends();
  }, []);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      {/* Workflow Steps Indicator */}
      <div className="flex justify-between items-center mb-8">
        <WorkflowStep icon={<ShoppingBag />} label="Discovery" active={step === 'discovery'} />
        <WorkflowStep icon={<Upload />} label="Visual Search" active={step === 'visual'} />
        <WorkflowStep icon={<Package />} label="Browse" active={step === 'browsing'} />
        <WorkflowStep icon={<Gift />} label="Gifting" active={step === 'gifting'} />
        <WorkflowStep icon={<CheckCircle />} label="Checkout" active={step === 'payment'} />
        <WorkflowStep icon={<Truck />} label="Fulfillment" active={step === 'completed'} />
      </div>

      {/* Step Content */}
      {step === 'discovery' && (
        <DiscoveryStep onDiscovery={handleDiscovery} trends={seasonalTrends} />
      )}

      {step === 'browsing' && (
        <BrowsingStep 
          recommendations={recommendations} 
          onAddToCart={addToCart}
          onVisualSearch={handleVisualSearch}
          onGiftMode={handleGiftMode}
        />
      )}

      {step === 'gifting' && (
        <GiftingStep suggestions={giftSuggestions} onAddToCart={addToCart} />
      )}

      {/* Cart Summary (always visible) */}
      {cart.length > 0 && (
        <CartSummary 
          cart={cart} 
          onVerify={verifyInventory}
          inventoryStatus={inventoryStatus}
          onCheckout={completeCheckout}
        />
      )}

      {/* Order Completed */}
      {step === 'completed' && orderStatus && (
        <OrderCompletedStep orderStatus={orderStatus} />
      )}
    </div>
  );
};

// Workflow Step Component
const WorkflowStep = ({ icon, label, active }) => (
  <div className={`flex flex-col items-center ${active ? 'text-blue-600' : 'text-gray-400'}`}>
    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${active ? 'bg-blue-100' : 'bg-gray-100'}`}>
      {icon}
    </div>
    <span className="text-sm mt-2">{label}</span>
  </div>
);

// Discovery Step
const DiscoveryStep = ({ onDiscovery, trends }) => (
  <div className="space-y-6">
    <h2 className="text-2xl font-bold">What are you shopping for?</h2>
    <div className="grid grid-cols-3 gap-4">
      <button onClick={() => onDiscovery('weekend_trip')} className="p-6 border-2 rounded-lg hover:border-blue-500">
        <div className="text-4xl mb-2">🏖️</div>
        <div className="font-semibold">Weekend Trip</div>
      </button>
      <button onClick={() => onDiscovery('office')} className="p-6 border-2 rounded-lg hover:border-blue-500">
        <div className="text-4xl mb-2">💼</div>
        <div className="font-semibold">Office Wear</div>
      </button>
      <button onClick={() => onDiscovery('party')} className="p-6 border-2 rounded-lg hover:border-blue-500">
        <div className="text-4xl mb-2">🎉</div>
        <div className="font-semibold">Party</div>
      </button>
    </div>
    
    {trends.length > 0 && (
      <div className="mt-8">
        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5" /> Seasonal Trends
        </h3>
        <div className="grid grid-cols-5 gap-4">
          {trends.slice(0, 5).map((item, idx) => (
            <div key={idx} className="border rounded-lg p-3">
              <div className="text-sm font-medium truncate">{item.ProductDisplayName}</div>
              <div className="text-lg font-bold text-blue-600">₹{item.price}</div>
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

// Browsing Step
const BrowsingStep = ({ recommendations, onAddToCart, onVisualSearch, onGiftMode }) => (
  <div className="space-y-6">
    <div className="flex justify-between items-center">
      <h2 className="text-2xl font-bold">Recommended For You</h2>
      <div className="space-x-2">
        <label className="px-4 py-2 bg-purple-600 text-white rounded-lg cursor-pointer hover:bg-purple-700">
          <Upload className="w-4 h-4 inline mr-2" />
          Upload Photo
          <input type="file" className="hidden" accept="image/*" onChange={(e) => e.target.files[0] && onVisualSearch(e.target.files[0])} />
        </label>
        <button onClick={onGiftMode} className="px-4 py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700">
          <Gift className="w-4 h-4 inline mr-2" />
          Gift Mode
        </button>
      </div>
    </div>
    
    <div className="grid grid-cols-3 gap-6">
      {recommendations.map((product, idx) => (
        <div key={idx} className="border rounded-lg p-4 hover:shadow-lg transition">
          <div className="aspect-square bg-gray-100 rounded mb-3"></div>
          <h3 className="font-semibold text-sm mb-2 truncate">{product.ProductDisplayName || product.name}</h3>
          <div className="flex justify-between items-center">
            <span className="text-xl font-bold text-blue-600">₹{product.price}</span>
            <button onClick={() => onAddToCart(product)} className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">
              Add
            </button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// Gifting Step
const GiftingStep = ({ suggestions, onAddToCart }) => (
  <div className="space-y-6">
    <h2 className="text-2xl font-bold flex items-center gap-2">
      <Gift className="w-6 h-6" /> Perfect Gift Ideas
    </h2>
    <div className="grid grid-cols-3 gap-6">
      {suggestions.map((product, idx) => (
        <div key={idx} className="border-2 border-pink-200 rounded-lg p-4 hover:shadow-lg transition">
          <div className="aspect-square bg-gradient-to-br from-pink-50 to-purple-50 rounded mb-3"></div>
          <h3 className="font-semibold text-sm mb-2">{product.ProductDisplayName || product.name}</h3>
          <div className="flex justify-between items-center">
            <span className="text-xl font-bold text-pink-600">₹{product.price}</span>
            <button onClick={() => onAddToCart(product)} className="px-3 py-1 bg-pink-600 text-white rounded hover:bg-pink-700">
              Add
            </button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// Cart Summary
const CartSummary = ({ cart, onVerify, inventoryStatus, onCheckout }) => {
  const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  
  return (
    <div className="border-2 border-blue-200 rounded-lg p-6 bg-blue-50">
      <h3 className="text-xl font-bold mb-4">Your Cart ({cart.length} items)</h3>
      <div className="space-y-2 mb-4">
        {cart.map((item, idx) => (
          <div key={idx} className="flex justify-between text-sm">
            <span>{item.name}</span>
            <span className="font-semibold">₹{item.price}</span>
          </div>
        ))}
      </div>
      <div className="border-t pt-3 mb-4">
        <div className="flex justify-between text-lg font-bold">
          <span>Total:</span>
          <span>₹{total}</span>
        </div>
      </div>
      
      {!inventoryStatus && (
        <button onClick={onVerify} className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold">
          Verify Availability & Proceed
        </button>
      )}
      
      {inventoryStatus && inventoryStatus.all_available && (
        <div className="space-y-3">
          <div className="text-green-600 font-semibold">✓ All items are available!</div>
          {inventoryStatus.low_stock_alerts?.length > 0 && (
            <div className="text-orange-600 text-sm">
              ⚠️ Low stock alerts: {inventoryStatus.low_stock_alerts.length} items
            </div>
          )}
          <button onClick={onCheckout} className="w-full py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold">
            Complete Checkout
          </button>
        </div>
      )}
      
      {inventoryStatus && !inventoryStatus.all_available && (
        <div className="text-red-600 font-semibold">✗ Some items are out of stock</div>
      )}
    </div>
  );
};

// Order Completed Step
const OrderCompletedStep = ({ orderStatus }) => (
  <div className="text-center space-y-6 py-12">
    <div className="w-20 h-20 bg-green-100 rounded-full mx-auto flex items-center justify-center">
      <CheckCircle className="w-12 h-12 text-green-600" />
    </div>
    <h2 className="text-3xl font-bold text-green-600">Order Placed Successfully!</h2>
    <p className="text-xl text-gray-600">Order ID: {orderStatus.order_id}</p>
    <div className="max-w-md mx-auto bg-gray-50 rounded-lg p-6 text-left">
      <h3 className="font-semibold mb-3">Order Status:</h3>
      <ul className="space-y-2 text-sm">
        <li className="flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-600" />
          Payment Confirmed
        </li>
        <li className="flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-600" />
          Inventory Reserved
        </li>
        <li className="flex items-center gap-2">
          <Package className="w-4 h-4 text-blue-600" />
          Preparing for Shipment
        </li>
        <li className="flex items-center gap-2">
          <Truck className="w-4 h-4 text-gray-400" />
          Delivery (In Progress)
        </li>
      </ul>
    </div>
    <p className="text-gray-600">
      You'll receive styling suggestions for your purchases shortly!
    </p>
  </div>
);

export default ShoppingWorkflow;
