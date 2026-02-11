import { createContext, useContext, useState, useEffect } from 'react';
import API from '@/config/api';

const WishlistContext = createContext();

export const useWishlist = () => {
  const ctx = useContext(WishlistContext);
  if (!ctx) throw new Error('useWishlist must be used within WishlistProvider');
  return ctx;
};

export const WishlistProvider = ({ children }) => {
  const [items, setItems] = useState(() => {
    try {
      const raw = localStorage.getItem('ey_wishlist');
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem('ey_wishlist', JSON.stringify(items));
  }, [items]);

  const addToWishlist = (item) => {
    // Normalize image to backend images endpoint when needed
    const rawImage = item.image || item.image_url || null;
    let imageUrl = null;
    if (rawImage) {
      if (rawImage.startsWith('http') || rawImage.startsWith('/')) imageUrl = rawImage;
      else {
        const basename = rawImage.split('/').pop();
        imageUrl = `${API.DATA_API}/images/${basename}`;
      }
    }

    setItems((prev) => {
      if (prev.find((i) => i.sku === item.sku)) return prev;
      return [
        ...prev,
        {
          sku: item.sku,
          name: item.name || item.product_display_name || '',
          image: imageUrl,
        },
      ];
    });
  };

  const removeFromWishlist = (sku) => {
    setItems((prev) => prev.filter((i) => i.sku !== sku));
  };

  const clearWishlist = () => setItems([]);

  return (
    <WishlistContext.Provider value={{ items, addToWishlist, removeFromWishlist, clearWishlist }}>
      {children}
    </WishlistContext.Provider>
  );
};

// Note: no default export to keep module exports stable for React Fast Refresh
