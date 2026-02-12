import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ShoppingCart, Heart, Share2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useCart } from '@/contexts/CartContext.jsx';
import { useWishlist } from '@/contexts/WishlistContext.jsx';
import API_ENDPOINTS from '@/config/api';
import Navbar from '@/components/Navbar.jsx';

const ProductDetail = () => {
  const { sku } = useParams();
  const navigate = useNavigate();
  const { addToCart } = useCart();
  
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [addedToCart, setAddedToCart] = useState(false);
  const [selectedSize, setSelectedSize] = useState(null);
  const [selectedColor, setSelectedColor] = useState(null);
  const { addToWishlist } = useWishlist();

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        setLoading(true);
        // Fetch product directly by SKU using the proper API endpoint (which uses Supabase first, CSV fallback)
        const response = await fetch(`${API_ENDPOINTS.DATA_PRODUCTS}/${sku}`);
        
        if (!response.ok) {
          if (response.status === 404) {
            setError(`Product with SKU ${sku} not found`);
          } else {
            setError('Failed to load product details');
          }
          return;
        }
        
        const foundProduct = await response.json();
        setProduct(foundProduct);
      } catch (err) {
        console.error('Error fetching product:', err);
        setError('Failed to load product details');
      } finally {
        setLoading(false);
      }
    };

    if (sku) {
      fetchProduct();
    }
  }, [sku]);

  const handleAddToCart = () => {
    if (!product) return;
    // Ensure options are selected if sizes exist
    if (attributes.sizes && !selectedSize) {
      setError('Please select a size');
      return;
    }

    addToCart({
      sku: product.sku,
      name: product.product_display_name,
      price: parseFloat(product.price),
      quantity: parseInt(quantity),
      image: product.image_url,
      selectedOptions: { size: selectedSize, color: selectedColor },
    });
    
    setAddedToCart(true);
    setTimeout(() => setAddedToCart(false), 2000);
  };

  const handleQuantityChange = (change) => {
    const newQuantity = Math.max(1, quantity + change);
    setQuantity(newQuantity);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-yellow-50 pt-20">
        <div className="max-w-7xl mx-auto px-4 py-16">
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-red-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading product details...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-yellow-50 pt-20">
        <div className="max-w-7xl mx-auto px-4 py-16">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-white rounded-lg p-8 text-center max-w-2xl mx-auto"
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Product Not Found</h2>
            <p className="text-gray-600 mb-6">{error || 'The product you are looking for does not exist.'}</p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate('/products')}
              className="px-6 py-3 bg-red-700 text-white rounded-lg font-medium hover:bg-red-800 transition-colors"
            >
              Back to Products
            </motion.button>
          </motion.div>
        </div>
      </div>
    );
  }

  const discount = product.msrp && parseFloat(product.msrp) > parseFloat(product.price)
    ? Math.round((1 - parseFloat(product.price) / parseFloat(product.msrp)) * 100)
    : 0;

  // Parse attributes JSON if it exists
  let attributes = {};
  try {
    if (product.attributes && typeof product.attributes === 'string') {
      attributes = JSON.parse(product.attributes.replace(/'/g, '"'));
    }
  } catch (e) {
    console.log('Could not parse attributes');
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-yellow-50">
      <Navbar />
      
      <div className="pt-32 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-6"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate('/products')}
              className="flex items-center gap-2 text-red-600 hover:text-red-700 font-medium transition"
            >
              <ArrowLeft size={20} />
              Back to Products
            </motion.button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12"
          >
          {/* Product Image Section */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex flex-col gap-4"
          >
            <div className="w-full aspect-square bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg overflow-hidden flex items-center justify-center">
              <img
                src={`http://localhost:8007/images/${product.image_url.split('/').pop()}`}
                alt={product.product_display_name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%25%22 height=%22100%25%22%3E%3Crect fill=%22%23e5e7eb%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-family=%22Arial%22 font-size=%2216%22 fill=%22%23999%22%3EProduct Image Not Available%3C/text%3E%3C/svg%3E';
                }}
              />
            </div>

            {/* Wishlist & Share */}
            <div className="flex gap-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex-1 flex items-center justify-center gap-2 py-3 border-2 border-gray-300 rounded-lg font-medium text-gray-700 hover:border-red-600 hover:text-red-600 transition-colors"
              onClick={() => addToWishlist({ sku: product.sku, name: product.product_display_name, image: product.image_url })}
              >
                <Heart size={20} />
                Wishlist
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex-1 flex items-center justify-center gap-2 py-3 border-2 border-gray-300 rounded-lg font-medium text-gray-700 hover:border-red-600 hover:text-red-600 transition-colors"
              >
                <Share2 size={20} />
                Share
              </motion.button>
            </div>
          </motion.div>

          {/* Product Info Section */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            {/* Category Breadcrumb */}
            <div className="text-sm text-gray-600 mb-2">
              {product.category} {product.subcategory && `/ ${product.subcategory}`}
            </div>

            {/* Product Name */}
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">
              {product.product_display_name}
            </h1>

            {/* Brand */}
            {product.brand && (
              <p className="text-lg text-gray-600 mb-4">By {product.brand}</p>
            )}

            {/* Rating */}
            <div className="flex items-center gap-4 mb-6 pb-6 border-b">
              <div className="flex items-center gap-2">
                <div className="flex">
                  {[...Array(Math.floor(parseFloat(product.ratings) || 0))].map((_, i) => (
                    <span key={i} className="text-yellow-400 text-xl">★</span>
                  ))}
                </div>
                <span className="text-lg font-semibold text-gray-900">
                  {product.ratings || 'N/A'}
                </span>
              </div>
              <span className="text-gray-600">
                ({product.review_count || 0} customer reviews)
              </span>
            </div>

            {/* Price Section */}
            <div className="mb-6">
              <div className="flex items-baseline gap-4 mb-2">
                <span className="text-4xl font-bold text-gray-900">
                  ₹{Math.floor(parseFloat(product.price) || 0)}
                </span>
                {product.msrp && parseFloat(product.msrp) > parseFloat(product.price) && (
                  <>
                    <span className="text-2xl text-gray-500 line-through">
                      ₹{Math.floor(parseFloat(product.msrp))}
                    </span>
                    <span className="text-xl font-bold text-red-600 bg-red-50 px-3 py-1 rounded">
                      {discount}% OFF
                    </span>
                  </>
                )}
              </div>
              <p className="text-green-700 font-medium">In Stock</p>
            </div>

            {/* Product Attributes */}
            {(product.base_colour || product.article_type) && (
              <div className="mb-6 pb-6 border-b space-y-4">
                {product.base_colour && (
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 mb-2">
                      Color
                    </label>
                    <div className="flex gap-3">
                      <button
                        onClick={() => setSelectedColor(product.base_colour)}
                        className={`px-4 py-2 border-2 rounded-lg font-medium ${
                          selectedColor === product.base_colour ? 'border-red-600 bg-red-50' : 'border-gray-300'
                        }`}
                      >
                        {product.base_colour}
                      </button>
                    </div>
                  </div>
                )}

                {attributes.sizes && (
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 mb-2">
                      Size
                    </label>
                    <div className="flex gap-3 flex-wrap">
                      {attributes.sizes.split(',').map((size) => {
                        const s = size.trim();
                        return (
                          <button
                            key={s}
                            onClick={() => setSelectedSize(s)}
                            className={`px-4 py-2 border-2 rounded-lg font-medium ${
                              selectedSize === s ? 'border-red-600 bg-red-50' : 'border-gray-300 hover:border-red-600'
                            }`}
                          >
                            {s}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Quantity Selector */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-gray-900 mb-3">
                Quantity
              </label>
              <div className="flex items-center gap-4 w-fit border border-gray-300 rounded-lg p-2">
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={() => handleQuantityChange(-1)}
                  className="px-3 py-1 text-gray-600 hover:text-gray-900 text-xl"
                >
                  −
                </motion.button>
                <span className="px-4 py-1 font-semibold text-lg w-12 text-center">
                  {quantity}
                </span>
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={() => handleQuantityChange(1)}
                  className="px-3 py-1 text-gray-600 hover:text-gray-900 text-xl"
                >
                  +
                </motion.button>
              </div>
            </div>

            {/* Add to Cart Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleAddToCart}
              className={`w-full py-4 px-6 rounded-lg font-bold text-lg flex items-center justify-center gap-2 transition-all ${
                addedToCart
                  ? 'bg-green-600 text-white'
                  : 'bg-red-700 text-white hover:bg-red-800'
              }`}
            >
              <ShoppingCart size={24} />
              {addedToCart ? 'Added to Cart!' : 'Add to Cart'}
            </motion.button>

            {/* Product Details Tab */}
            <div className="mt-8 pt-8 border-t">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Product Details</h3>
              <div className="space-y-3">
                {product.article_type && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Article Type</span>
                    <span className="font-semibold text-gray-900">{product.article_type}</span>
                  </div>
                )}
                
                {product.usage && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Usage</span>
                    <span className="font-semibold text-gray-900">{product.usage}</span>
                  </div>
                )}

                {product.season && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Season</span>
                    <span className="font-semibold text-gray-900">{product.season}</span>
                  </div>
                )}

                {product.year && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Year</span>
                    <span className="font-semibold text-gray-900">{Math.floor(product.year)}</span>
                  </div>
                )}

                {attributes.material && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Material</span>
                    <span className="font-semibold text-gray-900">{attributes.material}</span>
                  </div>
                )}

                {product.gender && (
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-gray-600">Gender</span>
                    <span className="font-semibold text-gray-900">{product.gender}</span>
                  </div>
                )}

                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-600">SKU</span>
                  <span className="font-semibold text-gray-900 font-mono text-sm">{product.sku}</span>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
        </div>
      </div>
    </div>
  );
};

export default ProductDetail;
