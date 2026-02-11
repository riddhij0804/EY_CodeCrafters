"""
Data API - Serves all CSV data from backend/data folder
Endpoints for products, customers, orders, stores, inventory
"""

from pathlib import Path
from typing import Dict, Any
import os
import requests

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uvicorn

app = FastAPI(
    title="Data API",
    description="Serves product, customer, order, and store data",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/health')
async def health():
    """Health endpoint for Data API."""
    try:
        # quick read to ensure data directory exists
        ok = (DATA_DIR.exists())
        return JSONResponse(status_code=200, content={"status": "healthy", "data_dir": str(DATA_DIR) if ok else None})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "unhealthy", "error": str(e)})


@app.exception_handler(Exception)
async def handle_exceptions(request, exc):
    return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error"})

# Data directory
DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "product_images"

# Supabase config (optional)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
FEATURE_SUPABASE_READ = os.getenv("FEATURE_SUPABASE_READ", "false").lower() in ("1", "true", "yes")

# Mount static files for images at /images endpoint
if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")


# Load CSV files
def load_csv(filename):
    """Load CSV file and return as list of dictionaries"""
    try:
        df = pd.read_csv(DATA_DIR / filename)
        records = df.to_dict(orient="records")
        
        # Clean NaN values from records (convert to None for JSON serialization)
        cleaned = []
        for record in records:
            clean_record = {}
            for key, value in record.items():
                # Check if value is NaN and convert to None
                if pd.isna(value):
                    clean_record[key] = None
                else:
                    clean_record[key] = value
            cleaned.append(clean_record)
        
        return cleaned
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading {filename}: {str(e)}")


def fetch_products_from_supabase():
    """Fetch all products from Supabase via REST API."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    url = f"{SUPABASE_URL}/rest/v1/products?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code in (200, 206):
            return resp.json()
        else:
            print(f"⚠ Supabase products fetch failed: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"⚠ Exception fetching from Supabase: {e}")
        return None


@app.get("/")
async def root():
    return {
        "service": "Data API",
        "version": "1.0.0",
        "endpoints": [
            "GET /products",
            "GET /orders",
            "GET /orders/{order_id}",
            "GET /stores",
            "GET /inventory"
        ]
    }


@app.get("/products")
async def get_products(
    request: Request,
    limit: int = Query(default=20, le=10000),
    offset: int = Query(default=0, ge=0),
    category: str = None,
    subcategory: str = None,
    gender: str = None,
    brand: str = None,
    min_price: int = None,
    max_price: int = None,
    min_rating: float = None
):
    """Get all products with optional filters (category, subcategory, gender, brand, price, rating)"""
    products = None

    # Try Supabase first if enabled
    if FEATURE_SUPABASE_READ:
        supa = fetch_products_from_supabase()
        if supa is not None:
            products = supa

    if products is None:
        products = load_csv("products.csv")
    
    # Apply filters
    if category:
        products = [p for p in products if (p.get("category") or p.get("masterCategory") or p.get("master_category") or "").lower() == category.lower()]
    if subcategory:
        products = [p for p in products if (p.get("sub_category") or p.get("subCategory") or p.get("subCategory") or "").lower() == subcategory.lower()]
    if gender:
        products = [p for p in products if (p.get("gender") or "").lower() == gender.lower()]
    if brand:
        products = [p for p in products if (p.get("brand") or "").lower() == brand.lower()]
    if min_price is not None:
        products = [p for p in products if p.get("price") and float(p.get("price", 0)) >= min_price]
    if max_price is not None:
        products = [p for p in products if p.get("price") and float(p.get("price", 0)) <= max_price]
    if min_rating is not None:
        products = [p for p in products if (p.get("ratings") or p.get("rating") is not None) and float(p.get("ratings", p.get("rating", 0))) >= min_rating]
    
    total = len(products)
    paginated = products[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "products": paginated
    }

@app.get("/products/{sku}")
async def get_product(request: Request, sku: str):
    """Get specific product by SKU"""
    # Try Supabase first if enabled
    if FEATURE_SUPABASE_READ and SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/products?select=*&sku=eq.{sku}"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0]
            # fallthrough to CSV
        except Exception as e:
            print(f"⚠ Supabase product fetch error: {e}")

    products = load_csv("products.csv")
    product = next((p for p in products if str(p.get('sku')) == str(sku)), None)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product

@app.get("/customers")
async def get_customers(limit: int = Query(default=20, le=10000), offset: int = Query(default=0, ge=0)):
    """Get all customers"""
    customers = load_csv("customers.csv")
    total = len(customers)
    paginated = customers[offset:offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "customers": paginated
    }

@app.get("/customers/{customer_id}")
async def get_customer(customer_id: int):
    """Get specific customer"""
    customers = load_csv("customers.csv")
    customer = next((c for c in customers if c['customer_id'] == customer_id), None)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer

@app.get("/orders")
async def get_orders(
    limit: int = Query(default=20, le=10000),
    offset: int = Query(default=0, ge=0),
    customer_id: int = None,
    status: str = None
):
    """Get all orders with optional filters"""
    orders = load_csv("orders.csv")
    
    # Apply filters
    if customer_id:
        orders = [o for o in orders if o.get('customer_id') == customer_id]
    if status:
        orders = [o for o in orders if o.get('status', '').lower() == status.lower()]
    
    total = len(orders)
    paginated = orders[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "orders": paginated
    }

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order"""
    orders = load_csv("orders.csv")
    order = next((o for o in orders if o['order_id'] == order_id), None)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@app.get("/stores")
async def get_stores():
    """Get all stores"""
    stores = load_csv("stores.csv")
    return {
        "total": len(stores),
        "stores": stores
    }

@app.get("/inventory")
async def get_inventory_data(limit: int = Query(default=20, le=10000), offset: int = Query(default=0, ge=0)):
    """Get inventory data"""
    inventory = load_csv("inventory.csv")
    total = len(inventory)
    paginated = inventory[offset:offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "inventory": paginated
    }

@app.get("/payments")
async def get_payments(limit: int = Query(default=20, le=10000), offset: int = Query(default=0, ge=0)):
    """Get payment records"""
    payments = load_csv("payments.csv")
    total = len(payments)
    paginated = payments[offset:offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "payments": paginated
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8007, reload=False)
