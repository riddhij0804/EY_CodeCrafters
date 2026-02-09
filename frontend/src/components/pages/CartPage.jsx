import { useNavigate } from 'react-router-dom';
import { useCart } from '@/contexts/CartContext.jsx';
import { ShoppingCart, Trash2, Plus, Minus, ArrowLeft } from 'lucide-react';
import Navbar from '@/components/Navbar.jsx';

const CartPage = () => {
  const navigate = useNavigate();
  const { cartItems, removeFromCart, updateQuantity, getCartTotal, getCartCount } = useCart();

  const formatINR = (amount) => {
    if (amount === undefined || amount === null) return '₹0';
    return parseFloat(amount).toLocaleString('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
    });
  };

  const handleCheckout = () => {
    if (cartItems.length === 0) return;
    navigate('/checkout');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-yellow-50 to-red-50">
      <Navbar />
      
      {/* Header */}
      <div className="pt-32 pb-8">
        <div className="max-w-4xl mx-auto px-4 py-6 bg-gradient-to-r from-red-600 to-orange-600 text-white shadow-md rounded-lg">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="hover:bg-white/10 p-2 rounded-full transition-colors"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <div className="flex items-center gap-3">
              <ShoppingCart className="w-8 h-8" />
              <div>
                <h1 className="text-2xl font-bold">Your Cart</h1>
                <p className="text-sm text-orange-100">
                  {getCartCount()} {getCartCount() === 1 ? 'item' : 'items'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cart Content */}
      <div className="max-w-4xl mx-auto px-4 pb-16">
        {cartItems.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-lg shadow-md">
            <ShoppingCart className="w-24 h-24 mx-auto text-gray-300 mb-4" />
            <h2 className="text-2xl font-semibold text-gray-700 mb-2">Your cart is empty</h2>
            <p className="text-gray-500 mb-6">Add some products to get started!</p>
            <button
              onClick={() => navigate('/products')}
              className="bg-gradient-to-r from-red-600 to-orange-600 text-white px-6 py-3 rounded-lg font-semibold hover:from-red-700 hover:to-orange-700 transition-all"
            >
              Continue Shopping
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Cart Items */}
            <div className="bg-white rounded-xl shadow-md overflow-hidden">
              {cartItems.map((item, idx) => (
                <div
                  key={item.sku}
                  className={`p-6 flex gap-4 ${idx !== 0 ? 'border-t border-gray-200' : ''}`}
                >
                  {/* Product Image */}
                  {item.image && (
                    <img
                      src={item.image}
                      alt={item.name}
                      className="w-24 h-24 object-cover rounded-lg"
                      onError={(e) => (e.target.style.display = 'none')}
                    />
                  )}

                  {/* Product Details */}
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg text-gray-900">{item.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">SKU: {item.sku}</p>
                    <p className="textont-bold text-green-600 mt-2">
                      {formatINR(item.unit_price)}
                    </p>

                    {/* Quantity Controls */}
                    <div className="flex items-center gap-4 mt-4">
                      <div className="flex items-center gap-2 border border-gray-300 rounded-lg">
                        <button
                          onClick={() => updateQuantity(item.sku, item.qty - 1)}
                          className="p-2 hover:bg-gray-100 transition-colors rounded-l-lg"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <span className="px-4 font-semibold">{item.qty}</span>
                        <button
                          onClick={() => updateQuantity(item.sku, item.qty + 1)}
                          className="p-2 hover:bg-gray-100 transition-colors rounded-r-lg"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>

                      <button
                        onClick={() => removeFromCart(item.sku)}
                        className="text-red-600 hover:text-red-700 p-2 rounded-lg hover:bg-red-50 transition-colors"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  {/* Item Total */}
                  <div className="text-right">
                    <p className="text-sm text-gray-500">Total</p>
                    <p className="text-xl font-bold text-gray-900">
                      {formatINR(item.price * item.qty)}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Cart Summary */}
            <div className="bg-white rounded-xl shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Order Summary</h2>
              
              <div className="space-y-3 mb-6">
                <div className="flex justify-between text-gray-700">
                  <span>Subtotal ({getCartCount()} items)</span>
                  <span className="font-semibold">{formatINR(getCartTotal())}</span>
                </div>
                <div className="border-t border-gray-200 pt-3">
                  <div className="flex justify-between text-lg font-bold text-gray-900">
                    <span>Total</span>
                    <span className="text-green-600">{formatINR(getCartTotal())}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={handleCheckout}
                className="w-full bg-gradient-to-r from-red-600 to-orange-600 text-white py-4 rounded-lg font-bold text-lg hover:from-red-700 hover:to-orange-700 transition-all shadow-lg hover:shadow-xl"
              >
                Proceed to Checkout
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CartPage;
