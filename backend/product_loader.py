"""
Unified product fetching layer supporting Supabase as primary source with CSV fallback.
Provides normalized product schema across all services.
"""

import os
import logging
from typing import Optional, List, Dict, Any
import pandas as pd
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try to import supabase, but don't fail if not available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)

# Supabase configuration - get from environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# CSV fallback paths
CSV_DIR = os.path.join(os.path.dirname(__file__), "data")
PRODUCTS_CSV = os.path.join(CSV_DIR, "products.csv")
IMAGES_CSV = os.path.join(CSV_DIR, "product_images")  # Directory for images


class ProductLoader:
    """Unified product loader with Supabase primary and CSV fallback."""
    
    def __init__(self):
        self.supabase_client: Optional[Client] = None
        self._products_cache: Optional[List[Dict[str, Any]]] = None
        self._init_supabase()
        self._load_csv_fallback()
    
    def _init_supabase(self):
        """Initialize Supabase client if credentials available."""
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase library not installed (supabase package not found)")
            return
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning(f"Supabase not configured - URL: {'set' if SUPABASE_URL else 'empty'}, Key: {'set' if SUPABASE_KEY else 'empty'}")
            return
        
        try:
            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("✓ Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Supabase: {e}")
            self.supabase_client = None
    
    def _load_csv_fallback(self):
        """Load products from CSV as fallback."""
        try:
            if os.path.exists(PRODUCTS_CSV):
                self.csv_df = pd.read_csv(PRODUCTS_CSV)
                logger.info(f"Loaded {len(self.csv_df)} products from CSV")
            else:
                self.csv_df = pd.DataFrame()
                logger.warning(f"Products CSV not found at {PRODUCTS_CSV}")
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            self.csv_df = pd.DataFrame()
    
    def _normalize_product(self, product: Dict[str, Any], source: str = "unknown") -> Dict[str, Any]:
        """Normalize product to standard schema.
        source: 'supabase' or 'csv' - helps determine how to handle image URLs
        """
        def _clean(val, default=None):
            try:
                if pd.isna(val):
                    return default
            except Exception:
                pass
            return val if val is not None else default

        sku = str(_clean(product.get("sku", product.get("id", "")), ""))

        # Standard schema for all products (clean NaN => None/defaults)
        raw_name = _clean(product.get("name", product.get("product_display_name", product.get("ProductDisplayName", ""))), "")
        raw_description = _clean(product.get("description", ""), "")
        raw_price = _clean(product.get("price", 0), 0)
        raw_rating = _clean(product.get("rating", product.get("ratings", 0)), 0)
        raw_stock = _clean(product.get("stock", product.get("quantity", 0)), 0)
        raw_category = _clean(product.get("category", product.get("masterCategory", product.get("master_category", ""))), "Other")
        
        # For images: Only use Supabase image URLs (which are already full URLs like https://...)
        # CSV images are ignored - we only want Supabase images
        raw_image = ""
        if source == "supabase":
            raw_image = _clean(product.get("image_url", product.get("image", "")), "")

        def _to_float(x, default=0.0):
            try:
                return float(x)
            except Exception:
                return float(default)

        def _to_int(x, default=0):
            try:
                return int(x)
            except Exception:
                return int(default)

        normalized = {
            "sku": sku,
            "name": str(raw_name) if raw_name is not None else "",
            "description": str(raw_description) if raw_description is not None else "",
            "price": _to_float(raw_price, 0),
            "rating": _to_float(raw_rating, 0),
            "ratings": _to_float(raw_rating, 0),  # Include both field names
            "stock": _to_int(raw_stock, 0),
            "category": str(raw_category) if raw_category is not None else "Other",
            "image_url": str(raw_image) if raw_image is not None else "",
            "product_url": f"/products/{sku}",  # Frontend navigation URL
        }
        
        # Preserve additional fields from original product
        # Preserve additional fields from original product but clean NaN values
        for key, value in product.items():
            if key not in normalized:
                try:
                    if pd.isna(value):
                        normalized[key] = None
                    else:
                        normalized[key] = value
                except Exception:
                    normalized[key] = value
        
        return normalized
    
    def _get_from_supabase(self, sku: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch products from Supabase."""
        if not self.supabase_client:
            return []
        
        try:
            if sku:
                response = self.supabase_client.table("products").select("*").eq("sku", sku).execute()
            else:
                response = self.supabase_client.table("products").select("*").execute()
            
            products = response.data if hasattr(response, 'data') else []
            return [self._normalize_product(p, source="supabase") for p in products]
        except Exception as e:
            logger.warning(f"Error fetching from Supabase: {e}")
            return []
    
    def _get_from_csv(self, sku: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch products from CSV fallback (images excluded - CSV images ignored per requirements)."""
        if self.csv_df.empty:
            return []
        
        try:
            if sku:
                filtered = self.csv_df[self.csv_df["sku"] == sku]
            else:
                filtered = self.csv_df
            
            return [self._normalize_product(row.to_dict(), source="csv") for _, row in filtered.iterrows()]
        except Exception as e:
            logger.error(f"Error fetching from CSV: {e}")
            return []
    
    def get_product(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get single product by SKU. Tries Supabase first, then CSV."""
        # Try Supabase first
        products = self._get_from_supabase(sku)
        if products:
            return products[0]
        
        # Fallback to CSV
        products = self._get_from_csv(sku)
        if products:
            return products[0]
        
        logger.warning(f"Product not found: {sku}")
        return None
    
    def get_all_products(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all products with pagination. Tries Supabase first, then CSV."""
        # Try Supabase first
        supabase_products = self._get_from_supabase()
        if supabase_products:
            return supabase_products[offset : offset + limit]
        
        # Fallback to CSV
        csv_products = self._get_from_csv()
        if csv_products:
            return csv_products[offset : offset + limit]
        
        logger.warning("No products available")
        return []
    
    def get_products_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get products by category."""
        all_products = self.get_all_products(limit=1000)
        filtered = [p for p in all_products if p.get("category", "").lower() == category.lower()]
        return filtered[:limit]
    
    def search_products(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search products by name."""
        all_products = self.get_all_products(limit=1000)
        query_lower = query.lower()
        filtered = [p for p in all_products if query_lower in p.get("name", "").lower()]
        return filtered[:limit]


# Singleton instance
_loader: Optional[ProductLoader] = None


def get_product_loader() -> ProductLoader:
    """Get or create the singleton ProductLoader instance."""
    global _loader
    if _loader is None:
        _loader = ProductLoader()
    return _loader


# Convenience functions
def get_product(sku: str) -> Optional[Dict[str, Any]]:
    """Get single product by SKU."""
    return get_product_loader().get_product(sku)


def get_all_products(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get all products."""
    return get_product_loader().get_all_products(limit, offset)


def get_products_by_category(category: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get products by category."""
    return get_product_loader().get_products_by_category(category, limit)


def search_products(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search products."""
    return get_product_loader().search_products(query, limit)
