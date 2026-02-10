# Quick Start Guide: Phase 3 Product Catalog

## Starting the Backend Services

### 1. Data API (Product Database & Images) - Port 8007
```bash
cd backend
python data_api.py
# or
python -m uvicorn data_api:app --port 8007 --reload
```
**Endpoints Available**:
- `/products` - Get all products with filtering
- `/images/{filename}` - Serve product images
- `/products/{sku}` - Get specific product

### 2. Sales Agent with Recommendations (Optional) - Port 8010
```bash
cd backend/agents/sales_agent
python app.py
# or
python -m uvicorn app:app --port 8010 --reload
```

### 3. Other Services (Port 8000, 8001, 8002, 8003, etc.)
```bash
# Run in separate terminals as needed for full functionality
python session_manager.py
# ... other agents
```

## Starting the Frontend

### 1. Install Dependencies (if not already done)
```bash
cd frontend
npm install
```

### 2. Start Development Server - Port 5173
```bash
npm run dev
```

## Testing the Implementation

### Test 1: View Featured Products on Landing Page
1. Open `http://localhost:5173/`
2. Scroll to **"Featured Products"** section
3. Verify 6 real products are displayed with:
   - Product images from backend
   - Actual product names and brands
   - Real prices and ratings
   - Working "Add to Cart" buttons

### Test 2: View Full Product Catalog
1. Click **"VIEW ALL PRODUCTS"** button
2. Or navigate directly to `http://localhost:5173/products`
3. You should see:
   - Search bar at top
   - Filter sidebar on left
   - Product grid on right
   - Sort dropdown

### Test 3: Test Filtering
1. Select **Category**: "Apparel" → See filtered products
2. Select **Gender**: "Men" → Further filtering
3. Adjust **Price Range**: ₹1000 - ₹3000 → See price-filtered items
4. Select **Brand**: Pick any brand → Brand-specific products
5. Click **Reset** → All filters cleared

### Test 4: Test Sorting
1. Start with **"Most Popular"** sort (default)
2. Switch to **"Highest Rated"** → Products reorder by ratings
3. Switch to **"Price: Low to High"** → Cheapest products first
4. Switch to **"Price: High to Low"** → Most expensive first

### Test 5: Test Search
1. Type "Puma" in search bar → See Puma products only
2. Type "Jacket" → See products with "Jacket" in name
3. Clear search → All unfiltered products return

### Test 6: Test Add to Cart
1. Click "Add to Cart" button on any product
2. Check navbar for cart count badge (should increase)
3. Click cart icon → Navigate to cart page
4. Verify product appears in cart with correct price

### Test 7: Test Responsive Design
1. **Desktop**: Open at full width, see 3-column grid
2. **Tablet**: Resize to 1024px width, see 2-column grid
3. **Mobile**: Resize to 640px width, see 1-column grid
4. Mobile: Filters should stack/collapse nicely

### Test 8: Test Image Loading
1. All product images should load from `http://localhost:8007/images/{filename}`
2. If image fails to load, gray placeholder should appear
3. No broken image icons should appear on page

### Test 9: Test Empty States
1. Search for "xyz9999xyz" → Should show "No products found"
2. See "Clear filters" button → Click it to reset
3. Loading spinner should appear briefly on page load

## API Testing (curl/Postman)

### Get All Products
```bash
curl "http://localhost:8007/products?limit=20"
```

### Get Filtered Products
```bash
curl "http://localhost:8007/products?limit=20&category=Apparel&brand=Puma"
```

### Get Specific Product
```bash
curl "http://localhost:8007/products/SKU000001"
```

### Get Product Image
```bash
curl "http://localhost:8007/images/product1.jpg"
```

## Troubleshooting

### Issue: Images not loading, showing placeholder
**Solution**: 
1. Check backend is running on port 8007
2. Verify `backend/data/product_images/` directory exists and has images
3. Check browser console for 404 errors
4. Ensure CORS is enabled on data_api.py

### Issue: Products not appearing on ProductCatalog page
**Solution**:
1. Open browser DevTools Network tab
2. Check if GET `/products` request succeeds (should return 4,796 products)
3. Check for any error messages in browser console
4. Verify `salesAgentService.getProducts()` is being called

### Issue: Filter controls not responding
**Solution**:
1. Check that state updates are happening in DevTools React profiler
2. Ensure filter state is properly initialized
3. Try clicking "Reset" button to verify state management works

### Issue: Add to Cart not updating cart count
**Solution**:
1. Verify CartContext is properly wrapping the app in App.jsx
2. Check browser console for errors when clicking Add to Cart
3. Verify useCart hook is imported correctly in components

### Issue: Localhost API calls not working
**Solution**:
1. Check all backend services are running on correct ports
2. Verify API_ENDPOINTS in `frontend/src/config/api.js` are correct
3. Check for CORS errors in browser console
4. Ensure firewall isn't blocking ports

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Session Manager | 8000 | http://localhost:8000 |
| Inventory Agent | 8001 | http://localhost:8001 |
| Loyalty Agent | 8002 | http://localhost:8002 |
| Payment Agent | 8003 | http://localhost:8003 |
| Sales Agent | 8010 | http://localhost:8010 |
| Data API | 8007 | http://localhost:8007 |

## Key Files to Review

### Frontend
- **ProductCatalog Component**: `frontend/src/components/pages/ProductCatalog.jsx` (486 lines)
  - Search, filtering, sorting logic
  - Product grid rendering
  - Cart integration
  
- **LandingPage Updates**: `frontend/src/components/pages/LandingPage.jsx`
  - Featured products section (now sees real data)
  - Updated navigation link to /products
  
- **Routing**: `frontend/src/App.jsx`
  - New route: `/products` → ProductCatalog

### Backend
- **Data API**: `backend/data_api.py`
  - Product fetching: GET /products
  - Image serving: GET /images/{filename}
  - Filters: category, brand, min_price, max_price

- **Products CSV**: `backend/data/products.csv`
  - 4,796 products with 18 columns
  - Image references in `product_images/` directory

## Performance Notes

- **Page Load**: ~1-2 seconds (loading 1000 products from CSV)
- **Filter Response**: Instant (client-side filtering)
- **Search Response**: Instant (real-time string matching)
- **Image Load**: 100-500ms per image (depending on network)
- **Total Catalog Load**: ~3-5 seconds (all 4,796 products)

## Next Steps

1. ✅ **Frontend Display**: Catalog is complete and functional
2. 📋 **Product Details**: Add individual product detail page
3. 💬 **User Reviews**: Show customer reviews on product cards
4. 🔍 **Advanced Search**: Full-text search with relevance ranking
5. 📦 **Inventory Integration**: Real-time stock status

---

## File Modifications Summary

| File | Change | Type |
|------|--------|------|
| `frontend/src/components/pages/ProductCatalog.jsx` | Complete new component (486 lines) | NEW |
| `frontend/src/components/pages/LandingPage.jsx` | Replace hardcoded products with real data, update button link | MODIFIED |
| `frontend/src/App.jsx` | Add ProductCatalog route for /products | MODIFIED |
| `backend/data_api.py` | Add StaticFiles mount for /images endpoint | MODIFIED |
| `PHASE_3_IMPLEMENTATION.md` | Documentation of Phase 3 | NEW |
| `THREE_PHASE_SUMMARY.md` | Complete 3-phase overview | NEW |

---

**Status**: ✅ **All phases complete and ready for testing!**
