"""
Data API - Serves all CSV data from backend/data folder
Endpoints for products, customers, orders, stores, inventory
"""

from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import uvicorn

from .utils.image_resolver import enrich_with_images

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

# Allowed image directories exposed via /assets endpoint
ASSET_FOLDERS = {"product_images", "reebok_images"}


# Load CSV files
def load_csv(filename):
    """Load CSV file and return as list of dictionaries"""
    try:
        df = pd.read_csv(DATA_DIR / filename)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading {filename}: {str(e)}")


def _format_product(record: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    enriched = dict(record)
    enrich_with_images(enriched, base_url=base_url)
    if enriched.get("primary_image"):
        enriched["image_url"] = enriched["primary_image"]
    return enriched

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

@app.get("/assets/{image_path:path}")
async def serve_product_image(image_path: str):
    """Serve product imagery from the data folder with path sanitisation."""
    safe_path = Path(image_path)

    root_folder = safe_path.parts[0]
    if root_folder not in ASSET_FOLDERS:
        raise HTTPException(status_code=404, detail="Image not found")

    target_path = (DATA_DIR / safe_path).resolve()
    allowed_base = (DATA_DIR / root_folder).resolve()

    if not str(target_path).startswith(str(allowed_base)) or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(target_path)


@app.get("/products")
async def get_products(
    request: Request,
    limit: int = Query(default=20, le=100),
    category: str = None
):
    """Get all products with optional category filter"""
    products = load_csv("products.csv")
    if category:
        products = [p for p in products if p.get("category", "").lower() == category.lower()]
    base_url = str(request.base_url).rstrip("/")
    formatted = [_format_product(p, base_url) for p in products[:limit]]
    return {
        "total": len(products),
        "limit": limit,
        "products": formatted
    }

@app.get("/products/{sku}")
async def get_product(request: Request, sku: str):
    """Get specific product by SKU"""
    products = load_csv("products.csv")
    product = next((p for p in products if p['sku'] == sku), None)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    base_url = str(request.base_url).rstrip("/")
    return _format_product(product, base_url)

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
