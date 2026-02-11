import { createContext, useContext, useState, useEffect } from 'react';
import API, { apiCall } from '@/config/api';

const CartContext = createContext();

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within CartProvider');
  }
  return context;
};

export const CartProvider = ({ children }) => {
  const genId = (sku) => `${sku}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;

  const [cartItems, setCartItems] = useState(() => {
    const saved = localStorage.getItem('ey_cart');
    const parsed = saved ? JSON.parse(saved) : [];
    return Array.isArray(parsed)
      ? parsed.map((item) => ({
          ...item,
          id: item.id || genId(item.sku),
          reservationStatus: item.reservationStatus || 'idle',
          reservationHoldId: item.reservationHoldId ?? null,
          reservationExpiresAt: item.reservationExpiresAt ?? null,
          reservationLocation: item.reservationLocation ?? null,
          reservedQuantity: item.reservedQuantity ?? 0,
        }))
      : [];
  });

  // Persist cart to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('ey_cart', JSON.stringify(cartItems));
  }, [cartItems]);

  const addToCart = (item) => {
    // Normalize incoming item fields so different components can call addToCart with different shapes
    const rawImage = item.image || item.image_url || item.img || null;
    let imageUrl = null;
    if (rawImage) {
      // If already absolute URL, use as-is
      if (rawImage.startsWith('http') || rawImage.startsWith('/')) {
        imageUrl = rawImage;
      } else {
        // Build backend images URL: /images/<basename>
        const basename = rawImage.split('/').pop();
        imageUrl = `${API.DATA_API}/images/${basename}`;
      }
    }

    const normalized = {
      sku: item.sku,
      name: item.name || item.product_display_name || item.title || '',
      unit_price: parseFloat(item.unit_price ?? item.price ?? item.amount ?? 0),
      qty: parseInt(item.qty ?? item.quantity ?? item.count ?? 1, 10),
      image: imageUrl,
      options: item.options || item.selectedOptions || {},
    };

    setCartItems((prev) => {
      const existing = prev.find(
        (i) => i.sku === normalized.sku && JSON.stringify(i.options) === JSON.stringify(normalized.options)
      );
      if (existing) {
        return prev.map((i) =>
          i.sku === normalized.sku && JSON.stringify(i.options) === JSON.stringify(normalized.options)
            ? { ...i, qty: i.qty + normalized.qty }
            : i
        );
      }

      return [
        ...prev,
        {
          id: genId(normalized.sku),
          ...normalized,
          reservationStatus: 'idle',
          reservationHoldId: null,
          reservationExpiresAt: null,
          reservationLocation: null,
          reservedQuantity: 0,
        },
      ];
    });
  };

  const removeFromCart = (id) => {
    setCartItems((prev) => prev.filter((i) => i.id !== id));
  };

  const updateQuantity = (id, qty) => {
    if (qty <= 0) {
      removeFromCart(id);
      return;
    }
    setCartItems((prev) =>
      prev.map((i) =>
        i.id === id
          ? {
              ...i,
              qty,
              reservedQuantity:
                i.reservedQuantity && i.reservedQuantity > qty ? qty : i.reservedQuantity,
            }
          : i
      )
    );
  };

  const updateItemMetadata = (id, updates) => {
    setCartItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...updates } : item)));
  };

  const clearCart = () => {
    setCartItems([]);
  };

  const getCartTotal = () => {
    return cartItems.reduce((sum, item) => {
      const price = parseFloat(item.unit_price ?? item.unitPrice ?? item.price ?? 0) || 0;
      const qty = parseInt(item.qty ?? 0, 10) || 0;
      return sum + price * qty;
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
        updateItemMetadata,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};
