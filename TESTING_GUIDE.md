# Quick Testing Guide: Product Pages

## Prerequisites
Ensure these services are running before testing:

```bash
# Terminal 1: Backend Data API (Port 8007)
cd backend
python data_api.py

# Terminal 2: Frontend Dev Server (Port 5173)
cd frontend
npm run dev
```

---

## Test Cases

### Test 1: Landing Page Featured Products ✓
**Expected**: Featured products display with real data

```
1. Navigate to http://localhost:5173/
2. Scroll to "Featured Products" section
3. Verify: See 6 products with images, names, prices, ratings
4. Verify: "View All Products" button is visible
```

### Test 2: Click Featured Product → Detail Page ✓
**Expected**: Clicking product navigates to detail page

```
1. On landing page featured section
2. Click anywhere on a product card (NOT the button)
3. Verify: Page navigates to /products/{sku}
4. Verify: ProductDetail page loads with that product's info
5. Verify: Back button returns to landing page
```

### Test 3: Featured Product Add to Cart ✓
**Expected**: Add to Cart works without navigating

```
1. On landing page featured section
2. Click "Add to Cart" button
3. Verify: Item added to cart (cart count increases)
4. Verify: Page does NOT navigate (stays on landing page)
5. Verify: Same product card still visible
```

### Test 4: View All Products Button ✓
**Expected**: Navigates to full product catalog

```
1. Click "View All Products" button on landing page
2. Verify: URL changes to /products
3. Verify: Page shows ProductCatalog component
4. Verify: See all 4796 products in grid (start loading if capped)
5. Verify: Filters sidebar is visible on left
6. Verify: Sort dropdown is visible
```

### Test 5: Full Catalog Grid ✓
**Expected**: All products display correctly

```
1. On /products page
2. Scroll through product grid
3. Verify: 
   - 1 column on mobile
   - 2 columns on tablet (768px)
   - 3 columns on desktop (1024px)
4. Verify: Each card shows image, name, brand, price, ratings
```

### Test 6: Click Catalog Product → Detail Page ✓
**Expected**: Detailed product page loads

```
1. On /products page
2. Click any product card
3. Verify: URL changes to /products/{sku}
4. Verify: ProductDetail page loads
5. Verify: Product name, image, details displayed
6. Verify: Back button appears in header
```

### Test 7: Catalog Add to Cart ✓
**Expected**: Add to cart works without navigating

```
1. On /products page
2. Click "Add to Cart" on any product
3. Verify: Cart count increases
4. Verify: Page stays on /products
5. Verify: Product grid still visible
6. Verify: Can add another product to cart
```

### Test 8: Product Detail Page Features ✓
**Expected**: All product information displays

```
On ProductDetail page (/products/{sku}):

3. Verify elements visible:
   - Back button (shows "Back to Products")
   - Product image (left side)
   - Product name (heading)
   - Brand name
   - Category breadcrumb
   - Ratings with review count
   - Price in ₹
   - MSRP if available (strikethrough)
   - Discount % if applicable
   - Color selection
   - Size selection (if available)
   - Material info
   - Quantity selector (+/−)
   - "Add to Cart" button
   - Wishlist button
   - Share button
   - Product details table (SKU, usage, season, etc)
```

### Test 9: Product Detail - Quantity Selector ✓
**Expected**: Can adjust quantity before adding

```
1. On ProductDetail page
2. Use +/− buttons to change quantity
3. Click "Add to Cart" with quantity > 1
4. Go to cart page
5. Verify: Product shows correct quantity
```

### Test 10: Product Detail - Back Button ✓
**Expected**: Navigate back to catalog

```
1. On ProductDetail page
2. Click "Back to Products" button
3. Verify: Returns to /products page
4. Verify: Maintains any filters/sorts from before clicking product
```

### Test 11: Catalog Search & Filter ✓
**Expected**: Searching filters products

```
1. On /products page
2. Type "Puma" in search bar
3. Verify: Grid shows only Puma products
4. Verify: Count shows filtered results
5. Clear search
6. Verify: All products return
```

### Test 12: Catalog Category Filter ✓
**Expected**: Category filtering works

```
1. On /products page
2. Click Category dropdown (sidebar)
3. Select "Apparel"
4. Verify: Grid shows only Apparel products
5. Products change to apply filter
6. Click Reset
7. Verify: All products return
```

### Test 13: Catalog Price Range Filter ✓
**Expected**: Price range filters products

```
1. On /products page
2. Enter Min Price: 1000
3. Enter Max Price: 3000
4. Verify: Products in that range display
5. Clear values
6. Verify: All price ranges return
```

### Test 14: Catalog Sorting ✓
**Expected**: Sorting reorders products

```
1. On /products page
2. Select "Price: Low to High"
3. Verify: Products reorder (cheapest first)
4. Select "Price: High to Low"
5. Verify: Products reorder (most expensive first)
6. Select "Highest Rated"
7. Verify: Products reorder by rating
```

### Test 15: Images Loading ✓
**Expected**: Product images load or show fallback

```
1. Any page with products
2. Verify: Images load from localhost:8007/images/
3. If image fails:
   - ProductCatalog: Shows gray placeholder
   - ProductDetail: Shows SVG placeholder
4. No broken image icons appear
```

### Test 16: Responsive Design - Mobile ✓
**Expected**: Mobile layout works

```
1. Resize browser to 375px width (or use DevTools)
2. On landing page:
   - Featured products: 1 column
   - All buttons clickable
3. On /products page:
   - Filters stack or hide
   - Product grid: 1 column
   - All controls accessible
4. On /products/{sku} page:
   - Image full width
   - Text readable
   - Buttons 100% width
```

### Test 17: Responsive Design - Tablet ✓
**Expected**: Tablet layout works

```
1. Resize browser to 768px width
2. On /products page:
   - Product grid: 2 columns
   - Sidebar visible
   - All filters work
3. Images and text at right size
4. All buttons clickable
```

### Test 18: Responsive Design - Desktop ✓
**Expected**: Desktop layout optimal

```
1. Full screen browser (1440px+)
2. On /products page:
   - Product grid: 3 columns
   - Sidebar fixed on left
   - Filters sticky while scrolling
3. Large images display properly
4. All interactions responsive
```

### Test 19: Empty State - No Products Match ✓
**Expected**: User-friendly empty message

```
1. On /products page
2. Search for "xyz9999xyz"
3. Verify: "No products found" message appears
4. Verify: "Clear filters" button visible
5. Click Clear Filters
6. Verify: All products return
```

### Test 20: Loading States ✓
**Expected**: Loading indicators appear during fetch

```
1. Hard refresh /products page
2. Verify: Spinner shows while loading
3. Verify: "Loading products..." message
4. Verify: Spinner disappears when done
5. On ProductDetail:
   - Loading spinner appears initially
   - Disappears when product loads
```

---

## Edge Cases

### Navigation from Product Detail
```
Test: Open ProductDetail directly via URL
1. Type in address bar: http://localhost:5173/products/SKU000001
2. Verify: Page loads that specific product
3. No need to go through catalog first
4. Back button works
```

### Missing Product Image
```
Test: Product with broken image URL
1. Open a product detail page
2. If image doesn't load:
   - ProductDetail: Shows SVG "Product Image Not Available"
   - Page layout intact
   - Rest of content visible
```

### Missing Product Attributes
```
Test: Product without all attributes
1. Open product lacking attributes
2. Verify: Missing fields don't break layout
3. Available fields display
4. No console errors
5. Graceful degradation
```

### Filter Combinations
```
Test: Multiple active filters
1. Select Category: Apparel
2. Select Gender: Men
3. Set Price: ₹2000-₹5000
4. Set Rating: 4+
5. Verify: All filters apply together
6. Product count reflects all constraints
7. Reset clears everything
```

---

## URLs to Test

| URL | Expected Page |
|-----|---|
| `http://localhost:5173/` | Landing page with 6 featured products |
| `http://localhost:5173/products` | Full catalog with 4796 products |
| `http://localhost:5173/products/SKU000001` | Product detail for SKU000001 |
| `http://localhost:5173/products/SKU000099` | Product detail for SKU000099 |
| `http://localhost:5173/products/INVALID` | "Product Not Found" error page |

---

## Console Checks

### Expected Logs
```javascript
// When loading products
console.log('Products loaded: 1000')
console.log('Unique categories: 22')
console.log('Filtering applied')

// Should NOT see errors like:
// Uncaught TypeError
// ReferenceError: navigate is not defined
// Cannot read properties of undefined
```

### Check DevTools
1. **Network tab**: 
   - ✓ GET /products (4,796 products)
   - ✓ GET /images/productX.jpg (200 OK)
   - No 404s or 500s

2. **Console tab**:
   - No red errors
   - No warnings about missing props
   - Image load errors OK (uses fallback)

3. **Elements tab**:
   - Navigation links have correct hrefs
   - Click triggers routing (no page reload)
   - Event listeners attached to cards

---

## Performance Notes

- **First Load**: ~2-3 seconds (loading 1000+ products)
- **Filter Response**: Instant (client-side)
- **Navigation**: Instant (React routing, no page reload)
- **Image Load**: 100-500ms per image

---

## Sign-Off Checklist

Before declaring complete:

- [ ] Landing page: 6 featured products display
- [ ] Featured product click: Navigates to detail
- [ ] "View All Products": Navigates to /products
- [ ] Catalog: Shows all 4,796 products
- [ ] Catalog product click: Navigates to detail
- [ ] Detail page: Shows complete product info
- [ ] Back button: Returns to catalog
- [ ] Add to Cart: Works without navigation
- [ ] Cart count: Updates correctly
- [ ] Filters: Work in catalog
- [ ] Sorting: Works in catalog
- [ ] Search: Works in catalog
- [ ] Responsive: Mobile/tablet/desktop all work
- [ ] Images: Load or show fallback
- [ ] No console errors
- [ ] No broken links

---

## Quick Bug Check

If something breaks:

1. **Check browser console** for errors
2. **Check terminal** for backend errors
3. **Verify localhost:8007 is running** (images need this)
4. **Clear browser cache** (Ctrl+Shift+Delete)
5. **Restart dev server** (Ctrl+C, npm run dev)
6. **Check network tab** for failed requests

---

Ready to test! 🚀
