"""
Data API - Serves all CSV data from backend/data folder
Endpoints for products, customers, orders, stores, inventory
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
from pathlib import Path
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

# Load CSV files
def load_csv(filename):
    """Load CSV file and return as list of dictionaries"""
    try:
        df = pd.read_csv(DATA_DIR / filename)
        return df.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading {filename}: {str(e)}")

@app.get("/")
async def root():
    return {
        "service": "Data API",
        "version": "1.0.0",
        "endpoints": [
            "GET /products",
            "GET /products/{sku}",
            "GET /customers",
            "GET /customers/{customer_id}",
            "GET /orders",
            "GET /orders/{order_id}",
            "GET /stores",
            "GET /inventory"
        ]
    }

@app.get("/products")
async def get_products(
    limit: int = Query(default=20, le=100),
    category: str = None,
    brand: str = None,
    min_price: float = None,
    max_price: float = None
):
    """Get all products with optional filters"""
    products = load_csv("products.csv")
    
    # Apply filters
    if category:
        products = [p for p in products if p.get('category', '').lower() == category.lower()]
    if brand:
        products = [p for p in products if p.get('brand', '').lower() == brand.lower()]
    if min_price:
        products = [p for p in products if p.get('price', 0) >= min_price]
    if max_price:
        products = [p for p in products if p.get('price', 0) <= max_price]
    
    return {
        "total": len(products),
        "limit": limit,
        "products": products[:limit]
    }

@app.get("/products/{sku}")
async def get_product(sku: str):
    """Get specific product by SKU"""
    products = load_csv("products.csv")
    product = next((p for p in products if p['sku'] == sku), None)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

@app.get("/customers")
async def get_customers(limit: int = Query(default=20, le=100)):
    """Get all customers"""
    customers = load_csv("customers.csv")
    return {
        "total": len(customers),
        "limit": limit,
        "customers": customers[:limit]
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
    limit: int = Query(default=20, le=100),
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
    
    return {
        "total": len(orders),
        "limit": limit,
        "orders": orders[:limit]
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
async def get_inventory_data(limit: int = Query(default=20, le=100)):
    """Get inventory data"""
    inventory = load_csv("inventory.csv")
    return {
        "total": len(inventory),
        "limit": limit,
        "inventory": inventory[:limit]
    }

@app.get("/payments")
async def get_payments(limit: int = Query(default=20, le=100)):
    """Get payment records"""
    payments = load_csv("payments.csv")
    return {
        "total": len(payments),
        "limit": limit,
        "payments": payments[:limit]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8007, reload=False)
