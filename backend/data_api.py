"""
Data API - Serves all CSV data from backend/data folder
Endpoints for products, customers, orders, stores, inventory
"""

from pathlib import Path
from typing import Dict, Any

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

# Data directory
DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = DATA_DIR / "product_images"

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
    products = load_csv("products.csv")
    
    # Apply filters
    if category:
        products = [p for p in products if p.get("category", "").lower() == category.lower()]
    if subcategory:
        products = [p for p in products if p.get("sub_category", "").lower() == subcategory.lower()]
    if gender:
        products = [p for p in products if p.get("gender", "").lower() == gender.lower()]
    if brand:
        products = [p for p in products if p.get("brand", "").lower() == brand.lower()]
    if min_price is not None:
        products = [p for p in products if p.get("price") and float(p.get("price", 0)) >= min_price]
    if max_price is not None:
        products = [p for p in products if p.get("price") and float(p.get("price", 0)) <= max_price]
    if min_rating is not None:
        products = [p for p in products if p.get("ratings") and float(p.get("ratings", 0)) >= min_rating]
    
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
    products = load_csv("products.csv")
    product = next((p for p in products if p['sku'] == sku), None)
    
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
