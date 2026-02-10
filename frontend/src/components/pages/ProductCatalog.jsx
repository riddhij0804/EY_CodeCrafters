import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, ChevronDown, ShoppingCart } from 'lucide-react';
import { motion } from 'framer-motion';
import { useCart } from '@/contexts/CartContext.jsx';
import Navbar from '@/components/Navbar.jsx';
import { salesAgentService } from '@/services/salesAgentService';

const ProductCatalog = () => {
  const navigate = useNavigate();
  const { addToCart, getCartCount } = useCart();
  
  // UI State
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('popularity');
  
  // Filter State
  const [filters, setFilters] = useState({
    category: '',
    sub_category: '',
    gender: '',
    brand: '',
    price_min: 0,
    price_max: 10000,
    rating_min: 0
  });
  
  // Product State
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [subCategories, setSubCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [genders, setGenders] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Fetch all products on mount
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const response = await salesAgentService.getProducts({ limit: 5000 });
        const allProducts = response.products || [];
        
        setProducts(allProducts);
        
        // Extract unique values for filters
        const uniqueCategories = [...new Set(allProducts.map(p => p.category).filter(Boolean))];
        const uniqueSubCategories = [...new Set(allProducts.map(p => p.sub_category).filter(Boolean))];
        const uniqueBrands = [...new Set(allProducts.map(p => p.brand).filter(Boolean))];
        const uniqueGenders = [...new Set(allProducts.map(p => p.gender).filter(Boolean))];
        
        setCategories(uniqueCategories.sort());
        setSubCategories(uniqueSubCategories.sort());
        setBrands(uniqueBrands.sort());
        setGenders(uniqueGenders.sort());
      } catch (error) {
        console.error('Error fetching products:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchProducts();
  }, []);
  
  // Apply filters and search
  useEffect(() => {
    let result = products;
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(p =>
        (p.product_display_name?.toLowerCase().includes(query) ||
         p.brand?.toLowerCase().includes(query) ||
         p.category?.toLowerCase().includes(query) ||
         p.sub_category?.toLowerCase().includes(query))
      );
    }
    
    // Category filter
    if (filters.category) {
      result = result.filter(p => p.category === filters.category);
    }
    
    // Sub-category filter
    if (filters.sub_category) {
      result = result.filter(p => p.sub_category === filters.sub_category);
    }
    
    // Gender filter
    if (filters.gender) {
      result = result.filter(p => p.gender?.toLowerCase() === filters.gender.toLowerCase());
    }
    
    // Brand filter
    if (filters.brand) {
      result = result.filter(p => p.brand === filters.brand);
    }
    
    // Price range
    const priceMin = parseFloat(filters.price_min) || 0;
    const priceMax = parseFloat(filters.price_max) || 10000;
    result = result.filter(p => {
      const price = parseFloat(p.price) || 0;
      return price >= priceMin && price <= priceMax;
    });
    
    // Rating filter
    if (filters.rating_min > 0) {
      result = result.filter(p => {
        const rating = parseFloat(p.ratings) || 0;
        return rating >= filters.rating_min;
      });
    }
    
    // Sorting
    switch (sortBy) {
      case 'price_low':
        result.sort((a, b) => (parseFloat(a.price) || 0) - (parseFloat(b.price) || 0));
        break;
      case 'price_high':
        result.sort((a, b) => (parseFloat(b.price) || 0) - (parseFloat(a.price) || 0));
        break;
      case 'ratings':
        result.sort((a, b) => (parseFloat(b.ratings) || 0) - (parseFloat(a.ratings) || 0));
        break;
      case 'popularity':
      default:
        result.sort((a, b) => (parseFloat(b.review_count) || 0) - (parseFloat(a.review_count) || 0));
        break;
    }
    
    setFilteredProducts(result);
  }, [products, searchQuery, filters, sortBy]);
  
  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
  };
  
  const resetFilters = () => {
    setFilters({
      category: '',
      sub_category: '',
      gender: '',
      brand: '',
      price_min: 0,
      price_max: 10000,
      rating_min: 0
    });
    setSearchQuery('');
  };
  
  const handleAddToCart = (product) => {
    addToCart({
      sku: product.sku,
      name: product.product_display_name,
      price: parseFloat(product.price),
      quantity: 1,
      image: product.image_url
    });
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-yellow-50">
      <Navbar />
      
      <div className="pt-32 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Our Products</h1>
            <p className="text-gray-600">Browse our complete collection of premium products</p>
          </motion.div>
          
          {/* Search Bar */}
          <div className="mb-8 relative">
            <Search className="absolute left-4 top-3.5 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search products by name, brand, or category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:border-red-600"
            />
          </div>
          
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Sidebar Filters */}
            <div className="lg:w-64 flex-shrink-0">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="bg-white p-6 rounded-lg shadow-md sticky top-32 max-h-[calc(100vh-200px)] overflow-y-auto"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
                  {(searchQuery || Object.values(filters).some(v => v)) && (
                    <button
                      onClick={resetFilters}
                      className="text-xs text-red-600 hover:text-red-700 font-medium"
                    >
                      Reset
                    </button>
                  )}
                </div>
                
                {/* Category */}
                <div className="mb-6 pb-6 border-b">
                  <label className="block text-sm font-medium text-gray-700 mb-3">Category</label>
                  <select
                    value={filters.category}
                    onChange={(e) => {
                      handleFilterChange('category', e.target.value);
                      handleFilterChange('sub_category', '');
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-red-600"
                  >
                    <option value="">All Categories</option>
                    {categories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
                
                {/* Sub-Category */}
                <div className="mb-6 pb-6 border-b">
                  <label className="block text-sm font-medium text-gray-700 mb-3">Sub-Category</label>
                  <select
                    value={filters.sub_category}
                    onChange={(e) => handleFilterChange('sub_category', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-red-600"
                  >
                    <option value="">All Sub-Categories</option>
                    {(filters.category 
                      ? subCategories.filter(sc => 
                          products.some(p => p.category === filters.category && p.sub_category === sc)
                        )
                      : subCategories
                    ).map(subCat => (
                      <option key={subCat} value={subCat}>{subCat}</option>
                    ))}
                  </select>
                </div>
                
                {/* Gender */}
                <div className="mb-6 pb-6 border-b">
                  <label className="block text-sm font-medium text-gray-700 mb-3">Gender</label>
                  <div className="space-y-2">
                    {genders.length > 0 ? (
                      <>
                        {genders.map(gender => (
                          <label key={gender} className="flex items-center">
                            <input
                              type="radio"
                              name="gender"
                              value={gender}
                              checked={filters.gender === gender}
                              onChange={(e) => handleFilterChange('gender', e.target.value)}
                              className="w-4 h-4"
                            />
                            <span className="ml-2 text-sm text-gray-600">{gender}</span>
                          </label>
                        ))}
                        <label className="flex items-center">
                          <input
                            type="radio"
                            name="gender"
                            value=""
                            checked={filters.gender === ''}
                            onChange={(e) => handleFilterChange('gender', e.target.value)}
                            className="w-4 h-4"
                          />
                          <span className="ml-2 text-sm text-gray-600">All</span>
                        </label>
                      </>
                    ) : (
                      <p className="text-sm text-gray-500">No gender data available</p>
                    )}
                  </div>
                </div>
                
                {/* Brand */}
                <div className="mb-6 pb-6 border-b">
                  <label className="block text-sm font-medium text-gray-700 mb-3">Brand</label>
                  <select
                    value={filters.brand}
                    onChange={(e) => handleFilterChange('brand', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-red-600"
                  >
                    <option value="">All Brands</option>
                    {brands.map(brand => (
                      <option key={brand} value={brand}>{brand}</option>
                    ))}
                  </select>
                </div>
                
                {/* Price Range */}
                <div className="mb-6 pb-6 border-b">
                  <label className="block text-sm font-medium text-gray-700 mb-3">Price Range</label>
                  <div className="space-y-2">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.price_min}
                      onChange={(e) => handleFilterChange('price_min', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.price_max}
                      onChange={(e) => handleFilterChange('price_max', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    />
                  </div>
                </div>
                
                {/* Rating */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-3">Minimum Rating</label>
                  <select
                    value={filters.rating_min}
                    onChange={(e) => handleFilterChange('rating_min', parseFloat(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-red-600"
                  >
                    <option value={0}>All Ratings</option>
                    <option value={3}>3+ Stars</option>
                    <option value={4}>4+ Stars</option>
                    <option value={4.5}>4.5+ Stars</option>
                  </select>
                </div>
              </motion.div>
            </div>
            
            {/* Main Content */}
            <div className="flex-1">
              {/* Sort Bar */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between mb-6 p-4 bg-white rounded-lg shadow-sm"
              >
                <span className="text-sm text-gray-600">
                  Showing {filteredProducts.length} products
                </span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-red-600"
                >
                  <option value="popularity">Most Popular</option>
                  <option value="ratings">Highest Rated</option>
                  <option value="price_low">Price: Low to High</option>
                  <option value="price_high">Price: High to Low</option>
                </select>
              </motion.div>
              
              {/* Products Grid */}
              {loading ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-red-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading products...</p>
                  </div>
                </div>
              ) : filteredProducts.length === 0 ? (
                <div className="flex items-center justify-center h-96 bg-white rounded-lg">
                  <div className="text-center">
                    <p className="text-gray-500 text-lg">No products found matching your filters</p>
                    <button
                      onClick={resetFilters}
                      className="mt-4 text-red-600 hover:text-red-700 font-medium"
                    >
                      Clear filters
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredProducts.map((product, index) => (
                    <motion.div
                      key={product.sku}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      whileHover={{ y: -8 }}
                      onClick={() => navigate(`/products/${product.sku}`)}
                      className="bg-white rounded-lg overflow-hidden shadow-md hover:shadow-xl transition-shadow group cursor-pointer"
                    >
                      {/* Product Image */}
                      <div className="relative h-64 sm:h-72 bg-gradient-to-br from-gray-100 to-gray-200 overflow-hidden">
                        <img
                          src={`http://localhost:8007/images/${product.image_url.split('/').pop()}`}
                          alt={product.product_display_name}
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                          onError={(e) => {
                            e.target.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%25%22 height=%22100%25%22%3E%3Crect fill=%22%23ccc%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-family=%22Arial%22 font-size=%2214%22 fill=%22%23666%22%3ENo Image%3C/text%3E%3C/svg%3E';
                          }}
                        />
                      </div>
                      
                      {/* Product Info */}
                      <div className="p-4 sm:p-5">
                        <p className="text-xs text-red-600 font-medium uppercase mb-1">
                          {product.category} • {product.sub_category}
                        </p>
                        <h3 className="text-sm sm:text-base font-semibold text-gray-900 mb-2 line-clamp-2">
                          {product.product_display_name}
                        </h3>
                        <p className="text-xs text-gray-500 mb-3">{product.brand}</p>
                        
                        {/* Rating */}
                        <div className="flex items-center gap-2 mb-3">
                          <div className="flex items-center">
                            {[...Array(Math.floor(parseFloat(product.ratings) || 0))].map((_, i) => (
                              <span key={i} className="text-yellow-400 text-sm">★</span>
                            ))}
                          </div>
                          <span className="text-xs text-gray-600">
                            {product.ratings || 'N/A'} ({product.review_count || 0} reviews)
                          </span>
                        </div>
                        
                        {/* Price */}
                        <div className="flex items-center gap-2 mb-4">
                          <span className="text-lg font-bold text-gray-900">
                            ₹{Math.floor(parseFloat(product.price) || 0)}
                          </span>
                          {product.msrp && parseFloat(product.msrp) > parseFloat(product.price) && (
                            <>
                              <span className="text-sm text-gray-500 line-through">
                                ₹{Math.floor(parseFloat(product.msrp))}
                              </span>
                              <span className="text-xs font-bold text-red-600">
                                {Math.round((1 - parseFloat(product.price) / parseFloat(product.msrp)) * 100)}% OFF
                              </span>
                            </>
                          )}
                        </div>
                        
                        {/* Add to Cart Button */}
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddToCart(product);
                          }}
                          className="w-full bg-red-700 hover:bg-red-800 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                        >
                          <ShoppingCart size={16} />
                          Add to Cart
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductCatalog;
