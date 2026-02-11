# Seed Inventory from CSV files
# Loads merged_products_902_rows.csv and inventory_realistic.csv into Redis

import csv
import sys
import os
from pathlib import Path

# Add parent directory to path to import redis_utils
sys.path.insert(0, str(Path(__file__).parent))
import redis_utils


def seed_online_inventory():
    """Seed online inventory from products.csv (default qty = 500)."""
    
    csv_path = Path(__file__).parent.parent.parent.parent / "data" / "products.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return 0
    
    count = 0
    print(f"📦 Loading online inventory from {csv_path.name}...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            sku = row['sku']
            
            # Set default online stock to 500 for all products
            redis_utils.set_stock(sku, 500, "online")
            count += 1
            
            if count % 100 == 0:
                print(f"  ✓ Loaded {count} SKUs...")
    
    print(f"✅ Online inventory loaded: {count} SKUs (default 500 units each)\n")
    return count


def seed_store_inventory():
    """Seed store inventory from inventory.csv or inventory_full.csv (preferred).

    The script will use `inventory_full.csv` when available (this file contains
    per-store rows) otherwise it falls back to `inventory.csv`.
    """
    # Prefer the comprehensive inventory_full.csv if present
    base = Path(__file__).parent.parent.parent.parent / "data"
    csv_full = base / "inventory_full.csv"
    csv_default = base / "inventory.csv"

    if csv_full.exists():
        csv_path = csv_full
        print(f"Using inventory_full.csv for store seeding: {csv_path}")
    else:
        csv_path = csv_default
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return 0
    
    count = 0
    stores_seen = set()
    
    print(f"🏬 Loading store inventory from {csv_path.name}...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # inventory_full.csv uses header 'quantity'; other CSVs may vary
            sku = row.get('sku')
            store_id = row.get('store_id')
            quantity_raw = (
                row.get('qty')
                or row.get('quantity')
                or row.get('Quantity')
                or row.get('QTY')
            )

            if not sku or not store_id:
                continue

            try:
                qty = int(quantity_raw)
            except (TypeError, ValueError):
                qty = 0
            
            # Set store stock
            # IMPORTANT: Pass just "STORE_MUMBAI", not "store:STORE_MUMBAI"
            # The set_stock function adds "store:" prefix automatically
            redis_utils.set_stock(sku, qty, store_id)
            
            count += 1
            stores_seen.add(store_id)
            
            if count % 500 == 0:
                print(f"  ✓ Loaded {count} store entries...")
    
    print(f"✅ Store inventory loaded: {count} entries across {len(stores_seen)} stores\n")
    return count


def verify_sample():
    """Verify sample inventory data."""
    print("🔍 Verifying sample inventory...")
    
    sample_skus = ["SKU000001", "SKU000002", "SKU000003"]
    
    for sku in sample_skus:
        stock = redis_utils.get_stock(sku)
        total = stock["online"] + sum(stock["stores"].values())
        
        print(f"  {sku}:")
        print(f"    Online: {stock['online']}")
        print(f"    Stores: {len(stock['stores'])} locations")
        print(f"    Total: {total}")
    
    print()


def main():
    """Main seeding function."""
    print("=" * 60)
    print("🌱 INVENTORY SEEDING SCRIPT")
    print("=" * 60)
    print()
    
    # Check Redis connection
    if not redis_utils.check_redis_health():
        print("❌ Redis connection failed. Check REDIS_URL in .env")
        sys.exit(1)
    
    print("✅ Redis connected\n")
    
    # Seed data
    online_count = seed_online_inventory()
    store_count = seed_store_inventory()
    
    # Verify
    verify_sample()
    
    print("=" * 60)
    print(f"✅ SEEDING COMPLETE")
    print(f"   • Online inventory: {online_count} SKUs")
    print(f"   • Store inventory: {store_count} entries")
    print("=" * 60)
    print()
    print("🚀 Run the inventory server with:")
    print("   python app.py")
    print()


if __name__ == "__main__":
    main()
