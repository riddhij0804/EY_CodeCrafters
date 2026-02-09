#!/usr/bin/env python3
"""
Seed Supabase PRODUCTS table from CSV.
Safely clears existing data and inserts new products.

Run:
python seed_products_supabase.py
"""

import os
import csv
import sys
import json
import ast
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import requests

# ==========================================
# LOAD ENV
# ==========================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip('"')
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip().strip('"')

DATA_DIR = Path(__file__).parent / "data"
PRODUCT_CSV = "products.csv"

BATCH_SIZE = 100

# EXACT SUPABASE SCHEMA (DO NOT CHANGE)
ALLOWED_COLUMNS = {
    "sku",
    "product_display_name",
    "brand",
    "category",
    "subcategory",
    "season",
    "usage",
    "price",
    "msrp",
    "currency",
    "attributes",
    "image_url",
    "ratings",
    "review_count",
}

# ==========================================
# HELPERS
# ==========================================

def get_headers():
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }

def validate_env():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("❌ SUPABASE_URL or SUPABASE_ANON_KEY missing")
        sys.exit(1)
    print("✅ Supabase config loaded")

def parse_attributes(value):
    """
    Safely parse attributes column:
    - Accepts JSON
    - Accepts Python dict strings
    - Never crashes
    """
    if value is None or value == "":
        return None

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        # Try JSON first
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

        # Try Python literal dict
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    return None

def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    clean = {}

    for k, v in row.items():
        if k not in ALLOWED_COLUMNS:
            continue  # DROP unknown columns

        if v is None or v == "":
            clean[k] = None
            continue

        if k in ["price", "msrp", "ratings"]:
            try:
                clean[k] = float(v)
            except ValueError:
                clean[k] = None

        elif k == "review_count":
            try:
                clean[k] = int(v)
            except ValueError:
                clean[k] = None

        elif k == "attributes":
            clean[k] = parse_attributes(v)

        else:
            clean[k] = v

    return clean

def read_products_csv() -> List[Dict[str, Any]]:
    path = DATA_DIR / PRODUCT_CSV
    if not path.exists():
        print(f"❌ CSV not found: {path}")
        sys.exit(1)

    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(normalize_row(row))

    print(f"✅ Loaded {len(rows)} products from CSV")
    return rows

def clear_products_table():
    url = f"{SUPABASE_URL}/rest/v1/products?sku=not.is.null"
    r = requests.delete(url, headers=get_headers())

    if r.status_code in [200, 204]:
        print("🧹 Old products cleared")
    else:
        print(f"⚠️ Clear failed: {r.status_code} {r.text[:200]}")

def insert_batch(batch: List[Dict[str, Any]]) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/products"
    r = requests.post(url, headers=get_headers(), json=batch)

    if r.status_code not in [200, 201]:
        print(f"❌ Insert failed: {r.status_code}")
        print(r.text[:300])
        return False

    return True

# ==========================================
# MAIN
# ==========================================

def main():
    print("\n🌱 SEEDING PRODUCTS TABLE\n")

    validate_env()
    products = read_products_csv()
    clear_products_table()

    inserted = 0
    for i in range(0, len(products), BATCH_SIZE):
        batch = products[i:i + BATCH_SIZE]
        if not insert_batch(batch):
            print("❌ Stopping due to error")
            sys.exit(1)

        inserted += len(batch)
        print(f"✅ Inserted {inserted}/{len(products)}")

    print("\n🎉 PRODUCTS SEEDING COMPLETE")
    print(f"Total products inserted: {inserted}\n")

if __name__ == "__main__":
    main()
