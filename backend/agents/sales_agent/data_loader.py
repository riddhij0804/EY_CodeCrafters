"""
CSV Data Loader for Member 4 Components
Loads all data from backend/data folder into memory for production-safe operations
"""
import csv
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

    # ...existing code...

logger = logging.getLogger(__name__)

    # ...existing code...


class CSVDataLoader:
    """
    Centralized data loader for all Member 4 components
    Loads data from actual CSV files in data folder
    """
    
    def __init__(self):
        # Get data directory path (../../data from sales_agent folder)
        current_dir = os.path.dirname(__file__)
        self.data_dir = os.path.abspath(os.path.join(current_dir, '..', '..', 'data'))
        
        # Data stores
        self.orders = {}
        self.payments = {}
        self.customers = {}
        self.inventory = {}
        self.products = {}
        self.stores = {}
        self.idempotency = {}
        
        # Load all data
        self._load_all_data()
        
        logger.info(f"Data loaded from {self.data_dir}")
        logger.info(f"Orders: {len(self.orders)}, Payments: {len(self.payments)}, "
                   f"Products: {len(self.products)}, Inventory entries: {len(self.inventory)}")
    
    def _load_all_data(self):
        """Load all CSV files"""
        try:
            self._load_orders()
            self._load_payments()
            self._load_customers()
            self._load_inventory()
            self._load_products()
            self._load_idempotency()
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def _load_orders(self):
        """Load orders.csv"""
        filepath = os.path.join(self.data_dir, 'orders.csv')
        if not os.path.exists(filepath):
            logger.warning(f"Orders file not found: {filepath}")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                order_id = row['order_id']
                
                # Parse JSON items (handle double quotes)
                items_str = row['items'].replace('""', '"')
                items = json.loads(items_str)
                
                self.orders[order_id] = {
                    'order_id': order_id,
                    'customer_id': row['customer_id'],
                    'items': items,
                    'total_amount': float(row['total_amount']),
                    'status': row['status'],  # placed, paid, delivered, cancelled, etc.
                    'created_at': row['created_at']
                }
        
        logger.info(f"Loaded {len(self.orders)} orders")
    
    def _load_payments(self):
        """Load payments.csv"""
        filepath = os.path.join(self.data_dir, 'payments.csv')
        if not os.path.exists(filepath):
            logger.warning(f"Payments file not found: {filepath}")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                payment_id = row['payment_id']
                order_id = row['order_id']
                
                self.payments[payment_id] = {
                    'payment_id': payment_id,
                    'order_id': order_id,
                    'status': row['status'],  # success, failed, pending
                    'amount': float(row['amount_rupees']),
                    'discount': float(row['discount_applied']),
                    'gst': float(row['gst']),
                    'method': row['method'],  # upi, card, netbanking
                    'gateway_ref': row['gateway_ref'],
                    'idempotency_key': row['idempotency_key'],
                    'created_at': row['created_at']
                }
        
        logger.info(f"Loaded {len(self.payments)} payments")
    
    def _load_customers(self):
        """Load customers.csv"""
        filepath = os.path.join(self.data_dir, 'customers.csv')
        if not os.path.exists(filepath):
            logger.warning(f"Customers file not found: {filepath}")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                customer_id = row['customer_id']
                
                self.customers[customer_id] = {
                    'customer_id': customer_id,
                    'name': row['name'],
                    'age': int(row['age']),
                    'gender': row['gender'],
                    'city': row['city'],
                    'loyalty_tier': row['loyalty_tier'],  # Bronze, Silver, Gold
                    'loyalty_points': int(row['loyalty_points']),
                    'device_preference': row['device_preference'],
                    'total_spend': float(row['total_spend']),
                    'items_purchased': int(row['items_purchased']),
                    'average_rating': float(row['average_rating']),
                    'days_since_last_purchase': int(row['days_since_last_purchase']),
                    'satisfaction': row['satisfaction']  # Satisfied, Neutral, Unsatisfied
                }
        
        logger.info(f"Loaded {len(self.customers)} customers")
    
    def _load_inventory(self):
        """Load inventory.csv"""
        filepath = os.path.join(self.data_dir, 'inventory.csv')
        if not os.path.exists(filepath):
            logger.warning(f"Inventory file not found: {filepath}")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku']
                store_id = row['store_id']
                key = f"{sku}_{store_id}"
                
                self.inventory[key] = {
                    'sku': sku,
                    'store_id': store_id,
                    'qty': int(row['qty'])
                }
        
        logger.info(f"Loaded {len(self.inventory)} inventory entries")
    
    def _load_products(self):
        """Load products.csv"""
        filepath = os.path.join(self.data_dir, 'products.csv')
        if not os.path.exists(filepath):
            logger.warning(f"Products file not found: {filepath}")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku']
                
                # Parse attributes JSON if present
                attributes = {}
                if row['attributes']:
                    try:
                        attributes = json.loads(row['attributes'].replace("'", '"'))
                    except:
                        attributes = {}
                
                record = {
                    'sku': sku,
                    'name': row['ProductDisplayName'],
                    'brand': row['brand'],
                    'category': row['category'],
                    'subcategory': row['subcategory'],
                    'season': row['season'],
                    'usage': row['usage'],
                    'price': float(row['price']),
                    'msrp': float(row['msrp']),
                    'currency': row['currency'],
                    'attributes': attributes,
                    'ratings': float(row['ratings']),
                    'review_count': int(row['review count'])
                }
                self.products[sku] = record
        
        logger.info(f"Loaded {len(self.products)} products")
    
    def _load_idempotency(self):
        """Load idempotency.csv"""
        filepath = os.path.join(self.data_dir, 'idempotency.csv')
        if not os.path.exists(filepath):
            logger.warning(f"Idempotency file not found: {filepath}")
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row['idempotency_key']
                
                # Parse result JSON
                result_str = row['result'].replace('""', '"')
                result = json.loads(result_str)
                
                self.idempotency[key] = {
                    'idempotency_key': key,
                    'result': result,
                    'created_at': row['created_at']
                }
        
        logger.info(f"Loaded {len(self.idempotency)} idempotency records")
    
    # Helper methods for common queries
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_payment_by_order(self, order_id: str) -> Optional[Dict]:
        """Get payment for an order"""
        for payment in self.payments.values():
            if payment['order_id'] == order_id:
                return payment
        return None
    
    def get_customer(self, customer_id: str) -> Optional[Dict]:
        """Get customer by ID"""
        return self.customers.get(customer_id)
    
    def get_product(self, sku: str) -> Optional[Dict]:
        """Get product by SKU"""
        return self.products.get(sku)
    
    def get_inventory(self, sku: str, store_id: str) -> int:
        """Get inventory quantity for SKU at store"""
        key = f"{sku}_{store_id}"
        inv = self.inventory.get(key, {})
        return inv.get('qty', 0)
    
    def find_stores_with_stock(self, sku: str, min_qty: int = 1) -> List[Dict]:
        """Find all stores that have stock for a SKU"""
        stores = []
        for key, inv in self.inventory.items():
            if inv['sku'] == sku and inv['qty'] >= min_qty:
                stores.append({
                    'store_id': inv['store_id'],
                    'store_name': inv['store_id'].replace('STORE_', '').title(),
                    'available_qty': inv['qty']
                })
        return stores
    
    def find_similar_products(self, sku: str, limit: int = 3) -> List[Dict]:
        """Find similar products (same category)"""
        product = self.get_product(sku)
        if not product:
            return []
        
        similar = []
        for other_sku, other_product in self.products.items():
            if (other_sku != sku and 
                other_product['category'] == product['category'] and
                other_product['subcategory'] == product['subcategory']):
                similar.append({
                    'sku': other_sku,
                    'name': other_product['name'],
                    'price': other_product['price'],
                    'image_url': other_product['image_url'],
                    'ratings': other_product['ratings']
                })
                if len(similar) >= limit:
                    break
        
        return similar
    
    def get_customer_loyalty_info(self, customer_id: str) -> Dict:
        """Get customer loyalty tier and points"""
        customer = self.get_customer(customer_id)
        if not customer:
            return {'tier': 'Bronze', 'points': 0}
        
        return {
            'tier': customer['loyalty_tier'],
            'points': customer['loyalty_points'],
            'total_spend': customer['total_spend']
        }
    
    def check_idempotency_key(self, key: str) -> Optional[Dict]:
        """Check if idempotency key already used"""
        return self.idempotency.get(key)
    
    def get_orders_by_customer(self, customer_id: str) -> List[Dict]:
        """Get all orders for a customer"""
        return [order for order in self.orders.values() 
                if order['customer_id'] == customer_id]
    
    def get_failed_payments(self) -> List[Dict]:
        """Get all failed payments"""
        return [payment for payment in self.payments.values() 
                if payment['status'] == 'failed']
    
    def get_cancelled_orders(self) -> List[Dict]:
        """Get all cancelled orders"""
        return [order for order in self.orders.values() 
                if order['status'] == 'cancelled']


# Singleton instance
_data_loader = None

def get_data_loader() -> CSVDataLoader:
    """Get singleton data loader instance"""
    global _data_loader
    if _data_loader is None:
        _data_loader = CSVDataLoader()
    return _data_loader


if __name__ == "__main__":
    # Test data loading
    logging.basicConfig(level=logging.INFO)
    
    loader = get_data_loader()
    
    print("\n=== Data Loader Test ===")
    print(f"✓ Orders loaded: {len(loader.orders)}")
    print(f"✓ Payments loaded: {len(loader.payments)}")
    print(f"✓ Customers loaded: {len(loader.customers)}")
    print(f"✓ Products loaded: {len(loader.products)}")
    print(f"✓ Inventory entries: {len(loader.inventory)}")
    print(f"✓ Idempotency records: {len(loader.idempotency)}")
    
    # Test queries
    print("\n=== Sample Queries ===")
    if loader.orders:
        order_id = list(loader.orders.keys())[0]
        order = loader.get_order(order_id)
        print(f"✓ Order {order_id}: {order['total_amount']} INR, Status: {order['status']}")
    
    if loader.products:
        sku = list(loader.products.keys())[0]
        product = loader.get_product(sku)
        print(f"✓ Product {sku}: {product['name']}, Price: {product['price']} INR")
        
        # Find stores with stock
        stores = loader.find_stores_with_stock(sku)
        print(f"✓ {sku} available at {len(stores)} stores")
        
        # Find similar products
        similar = loader.find_similar_products(sku)
        print(f"✓ Found {len(similar)} similar products")
    
    print("\n=== Data Loader Ready! ===")
