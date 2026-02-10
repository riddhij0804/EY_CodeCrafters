import { createContext, useContext, useState, useEffect } from 'react';

const CartContext = createContext();

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  return context;
};

export const CartProvider = ({ children }) => {
  const [cartItems, setCartItems] = useState(() => {
    // Load cart from localStorage on init
    const saved = localStorage.getItem('ey_cart');
    return saved ? JSON.parse(saved) : [];
  });

  // Persist cart to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('ey_cart', JSON.stringify(cartItems));
  }, [cartItems]);

  const addToCart = (item) => {
    setCartItems((prev) => {
      const existing = prev.find((i) => i.sku === item.sku);
      if (existing) {
        // Update quantity if item already exists
        return prev.map((i) =>
          i.sku === item.sku ? { ...i, qty: i.qty + (item.qty || 1) } : i
        );
      }
      // Add new item with qty
      return [...prev, { ...item, qty: item.qty || 1 }];
    });
  };

  const removeFromCart = (sku) => {
    setCartItems((prev) => prev.filter((i) => i.sku !== sku));
  };

  const updateQuantity = (sku, qty) => {
    if (qty <= 0) {
      removeFromCart(sku);
      return;
    }
    setCartItems((prev) =>
      prev.map((i) => (i.sku === sku ? { ...i, qty } : i))
    );
  };

  const clearCart = () => {
    setCartItems([]);
  };

  const getCartTotal = () => {
    return cartItems.reduce((sum, item) => {
      const price = parseFloat(item.price || 0);
      return sum + price * item.qty;
    }, 0);
  };

  const getCartCount = () => {
    return cartItems.reduce((sum, item) => sum + item.qty, 0);
  };

  return (
    <CartContext.Provider
      value={{
        cartItems,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        getCartTotal,
        getCartCount,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};
