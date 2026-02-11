import { useWishlist } from '@/contexts/WishlistContext.jsx';
import Navbar from '@/components/Navbar.jsx';
import { Trash2 } from 'lucide-react';

const Wishlist = () => {
  const { items, removeFromWishlist, clearWishlist } = useWishlist();

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-yellow-50">
      <Navbar />
      <div className="pt-32 max-w-4xl mx-auto px-4">
        <h2 className="text-2xl font-bold mb-4">Your Wishlist</h2>
        {items.length === 0 ? (
          <p className="text-gray-600">Your wishlist is empty.</p>
        ) : (
          <div className="space-y-4">
            {items.map((it) => (
              <div key={it.sku} className="flex items-center gap-4 bg-white p-4 rounded-lg shadow">
                {it.image ? (
                  <img src={it.image} alt={it.name} className="w-20 h-20 object-cover rounded" />
                ) : (
                  <div className="w-20 h-20 bg-gray-100 rounded flex items-center justify-center text-sm">No Image</div>
                )}
                <div className="flex-1">
                  <div className="font-semibold">{it.name}</div>
                  <div className="text-xs text-gray-500">{it.sku}</div>
                </div>
                <button onClick={() => removeFromWishlist(it.sku)} className="p-2 text-red-600">
                  <Trash2 />
                </button>
              </div>
            ))}
            <div>
              <button onClick={clearWishlist} className="px-4 py-2 bg-red-600 text-white rounded">Clear Wishlist</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Wishlist;
