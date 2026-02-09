# Developer Quick Reference: Frontend Fixes

## TL;DR - What Changed

| What | Where | Change |
|------|-------|--------|
| Product Detail Page | NEW: `ProductDetail.jsx` | Complete new component (570 lines) |
| Product Catalog | `ProductCatalog.jsx` | +onClick navigation to detail |
| Landing Page | `LandingPage.jsx` | +onClick navigation to detail |
| Routing | `App.jsx` | +ProductDetail import, +/products/:sku route |

---

## Code Changes at a Glance

### Add onClick to Product Cards
```javascript
// In ProductCatalog.jsx and LandingPage.jsx

<motion.div onClick={() => navigate(`/products/${product.sku}`)}>
  {/* Product card content */}
</motion.div>
```

### Prevent Navigation on Button Click
```javascript
// In Add to Cart buttons

onClick={(e) => {
  e.stopPropagation();  // ← Key: Prevents bubble to parent
  handleAddToCart(product);
}}
```

### Create ProductDetail Component
```javascript
// In ProductDetail.jsx

const { sku } = useParams();  // ← Get SKU from URL
// Fetch product by SKU
// Display full details
```

### Add Routes
```javascript
// In App.jsx

<Route path="/products" element={<ProductCatalog />} />
<Route path="/products/:sku" element={<ProductDetail />} />
```

---

## File Locations

```
frontend/src/
├── components/pages/
│   ├── ProductDetail.jsx           ← NEW (570 lines)
│   ├── ProductCatalog.jsx          ← Modified (+2 lines)
│   ├── LandingPage.jsx             ← Modified (+2 lines)
│   └── ...
├── App.jsx                         ← Modified (+2 lines)
└── ...
```

---

## How It Works

### ProductCatalog Workflow
```
ComponentMount
  ↓
useEffect
  ↓
getProducts({ limit: 1000 })  ← Get all products
  ↓
setProducts(response)
  ↓
Render grid with onClick handlers
  ↓
User clicks card
  ↓
navigate(`/products/${sku}`)
  ↓
ProductDetail page loads
```

### ProductDetail Workflow
```
Route Match: /products/:sku
  ↓
ProductDetail component mounts
  ↓
useParams().sku  ← Extract SKU from URL
  ↓
useEffect
  ↓
Fetch all products  ← getProducts()
  ↓
Find product with matching SKU
  ↓
setProduct()
  ↓
Render details
```

### Add to Cart Without Navigation
```
Button clicked
  ↓
onClick={(e) => {
  e.stopPropagation();  ← <-- Prevents parent onClick
  handleAddToCart(product);
}}
  ↓
Event stops at button
  ↓
Parent card onClick NOT triggered
  ↓
No navigation occurs ✅
```

---

## Common Tasks

### Add New Filter to ProductCatalog
```javascript
// 1. Add to filter state
const [filters, setFilters] = useState({
  category: '',
  // ... existing filters
  newFilter: '',  // ← Add here
});

// 2. Add to filter UI (sidebar)
<select 
  value={filters.newFilter}
  onChange={(e) => handleFilterChange('newFilter', e.target.value)}
>
  <option value="">All</option>
  {/* Map options */}
</select>

// 3. Add to filtering logic (useEffect)
if (filters.newFilter) {
  result = result.filter(p => p.newFilter === filters.newFilter);
}
```

### Add Product Detail Field
```javascript
// In ProductDetail.jsx, in the details table section

{product.yourField && (
  <div className="flex justify-between py-2 border-b">
    <span className="text-gray-600">Field Label</span>
    <span className="font-semibold text-gray-900">
      {product.yourField}
    </span>
  </div>
)}
```

### Change Detail Page Layout
```javascript
// In ProductDetail.jsx grid:

// Current: 2-column (image + info)
className="grid grid-cols-1 lg:grid-cols-2 gap-8"

// Alternative: 3-column
className="grid grid-cols-1 lg:grid-cols-3 gap-8"

// Alternative: Single column
className="flex flex-col gap-8"
```

### Modify Product Card Click Behavior
```javascript
// Currently navigates to detail page
onClick={() => navigate(`/products/${product.sku}`)}

// Alternative: Open modal instead
onClick={() => setSelectedProduct(product)}

// Alternative: Show in sidebar
onClick={() => setDetailProduct(product)}
```

---

## Debugging Quick Tips

### Products Not Loading
```javascript
// Check in browser console:
console.log('Check API response:', response.products.length)

// If 0: API isn't returning data
// If >0: Data is there, check filtering logic
```

### Navigation Not Working
```javascript
// Verify useNavigate is imported
import { useNavigate } from 'react-router-dom';

// Verify navigate is called in component
const navigate = useNavigate();

// Check URL actually changes in browser address bar
```

### Images Not Displaying
```javascript
// Check image path formation:
const imagePath = `http://localhost:8007/images/${product.image_url.split('/').pop()}`;
console.log('Image path:', imagePath);

// Open URL in browser to verify:
// http://localhost:8007/images/product1.jpg

// Check backend is running (port 8007)
```

### "Add to Cart" Causing Navigation
```javascript
// Problem: onClick not using stopPropagation
onClick={() => handleAddToCart(product)}  // ❌

// Fix: Add stopPropagation
onClick={(e) => {
  e.stopPropagation();  // ← Add this
  handleAddToCart(product);
}}  // ✅
```

---

## Performance Tips

### Optimize Product Loading
```javascript
// Current: Loads 1000 products
const response = await getProducts({ limit: 1000 });

// For production: Implement pagination
// Page 1: getProducts({ limit: 50, offset: 0 })
// Page 2: getProducts({ limit: 50, offset: 50 })
```

### Optimize Image Loading
```javascript
// Current: All images load at once
// For production: Use intersection observer
// to lazy load images as user scrolls

import { useEffect, useRef } from 'react';

const imageRef = useRef();
useEffect(() => {
  const observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) {
      // Load image only when visible
      img.src = actualImagePath;
      observer.unobserve(img);
    }
  });
  observer.observe(imageRef.current);
}, []);
```

---

## Testing Tips

### Test Navigation
```javascript
// In browser DevTools Console:
window.location.pathname  // Current path

// After navigating:
window.location.pathname  // Should be /products

// For specific SKU:
window.location.pathname  // Should be /products/SKU000001
```

### Test Product Fetching
```javascript
// In browser DevTools Network tab:
// Look for: GET http://localhost:8007/products
// Should return: 4,796 products
// Status: 200 OK

// Response preview should show products array
```

### Test Event Propagation
```javascript
// Add to onClick handler:
onClick={(e) => {
  console.log('Event:', e);
  console.log('Target:', e.target);
  console.log('Parent:', e.currentTarget);
  // If stopPropagation works, should NOT
  // trigger parent onClick
}}
```

---

## Common Patterns

### Fetching Product by SKU
```javascript
// In ProductDetail.jsx

const [product, setProduct] = useState(null);

useEffect(() => {
  const fetchProduct = async () => {
    const response = await getProducts({ limit: 10000 });
    const found = response.products?.find(p => p.sku === sku);
    setProduct(found);
  };
  
  fetchProduct();
}, [sku]);  // ← Re-fetch if SKU changes
```

### Parsing Product Attributes
```javascript
// CSV has: attributes = "{'material': 'Cotton', ...}"
// Parse it:

let attributes = {};
try {
  if (product.attributes) {
    attributes = JSON.parse(
      product.attributes.replace(/'/g, '"')  // ← Single to double quotes
    );
  }
} catch (e) {
  console.warn('Could not parse attributes');
}

// Use it:
{attributes.material && <span>{attributes.material}</span>}
```

### Discount Calculation
```javascript
// Show discount if MSRP > price
const hasDiscount = product.msrp && 
                    parseFloat(product.msrp) > parseFloat(product.price);

if (hasDiscount) {
  const discount = Math.round(
    (1 - parseFloat(product.price) / parseFloat(product.msrp)) * 100
  );
  // Display: {discount}% OFF
}
```

---

## Code Standards Used

### Naming Conventions
- Components: `PascalCase` (ProductDetail, ProductCatalog)
- Files: `PascalCase.jsx` (ProductDetail.jsx)
- Imports: Destructured at top
- State: camelCase (selectedProduct, isLoading)
- Functions: camelCase (handleAddToCart, fetchProducts)
- Constants: UPPER_CASE (MAX_PRODUCTS = 10000)

### File Structure
```javascript
// Import statements (top)
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// Component function
export default function ComponentName() {
  // Hooks (useState, useEffect, etc)
  const [state, setState] = useState();
  
  // Functions
  const handleEvent = () => {};
  
  // Render
  return (
    <div>...</div>
  );
}
```

### Error Handling
```javascript
try {
  // Try to do something
  const data = await fetchData();
} catch (error) {
  // Handle error gracefully
  console.error('Error:', error);
  setError('Failed to load data');
} finally {
  // Always run
  setLoading(false);
}
```

---

## Version Control

### Commit Messages
```
✅ Implemented product detail page with SKU routing
✅ Added product card navigation to detail pages
✅ Enhanced catalog with filtering and search
❌ Fixed broken button (broken implies it was working)
```

### Branches
```
Feature: feature/product-details
Bugfix: fix/button-navigation
Docs: docs/product-page-guide
```

---

## Deployment Checklist

- [ ] All syntax valid (no console errors)
- [ ] All imports correct
- [ ] Routes defined in App.jsx
- [ ] Backend running on port 8007
- [ ] Images directory exists
- [ ] No hardcoded localhost (use env vars)
- [ ] Responsive design tested (mobile/tablet/desktop)
- [ ] Back button tested
- [ ] Add to cart tested
- [ ] Search/filter tested
- [ ] Navigation tested
- [ ] Error states tested

---

## Quick Help

### "How do I...?"

**...add a new route?**
```javascript
// In App.jsx Routes:
<Route path="/new-page" element={<NewPage />} />
```

**...navigate to a page?**
```javascript
// In component:
const navigate = useNavigate();
navigate('/products');  // or
navigate(`/products/${sku}`);
```

**...prevent event bubbling?**
```javascript
// In button:
onClick={(e) => {
  e.stopPropagation();
  doSomething();
}}
```

**...fetch data on mount?**
```javascript
// Use useEffect:
useEffect(() => {
  const fetchData = async () => {
    const data = await getProducts();
    setProducts(data);
  };
  fetchData();
}, []);  // Empty dependency array = runs once on mount
```

**...get URL parameter?**
```javascript
// In component:
const { sku } = useParams();  // For /products/:sku
// sku will be the actual SKU value
```

**...conditionally render?**
```javascript
// Use ternary:
{condition ? <ComponentIfTrue /> : <ComponentIfFalse />}

// Or &&:
{condition && <ComponentIfTrue />}
```

---

## Resources

- ProductDetail.jsx - Full component code (570 lines)
- ProductCatalog.jsx - Search/filter/sort component
- TESTING_GUIDE.md - Complete test cases
- BEFORE_AFTER.md - Visual user flow comparison
- FIXES_SUMMARY.md - Overview of all fixes

---

## Get Help

Check these files in this order:

1. **Quick question?** → This file (you're reading it!)
2. **Navigation not working?** → Check App.jsx routes
3. **Data not loading?** → Check API endpoint in browser
4. **Want to test?** → See TESTING_GUIDE.md
5. **Want visual comparison?** → See BEFORE_AFTER.md
6. **Full details?** → See FRONTEND_FIXES_GUIDE.md

---

Done! Happy coding! 🚀
