"""
Inventory repository: reads stock from Supabase.

Expects an 'inventory' table with columns: sku, store_id, quantity
"""
from typing import Dict, Any, Optional
from ..supabase_client import select, is_enabled


def _aggregate_rows(rows) -> Dict[str, Any]:
    """
    Aggregate inventory rows into {online, stores, total} format.
    
    Rows should have: sku, store_id, quantity
    store_id='ONLINE' or similar → online stock
    store_id='STORE_MUMBAI' etc → store stock
    """
    result = {"online": 0, "stores": {}, "total": 0}
    
    for row in rows:
        try:
            qty = int(row.get("quantity") or row.get("qty") or 0)
        except (ValueError, TypeError):
            qty = 0
        
        store_id = str(row.get("store_id", "")).upper()
        
        if store_id == "ONLINE":
            result["online"] += qty
        else:
            result["stores"][store_id] = result["stores"].get(store_id, 0) + qty
        
        result["total"] += qty
    
    return result


def get_stock(sku: str) -> Optional[Dict[str, Any]]:
    """
    Get stock for a SKU from Supabase.
    
    Returns:
        {"online": int, "stores": {store_id: qty}, "total": int}
        or None on error/empty
    """
    if not is_enabled():
        return None
    
    try:
        rows = select("inventory", params=f"sku=eq.{sku}", columns="sku,store_id,quantity")
        if not rows:
            print(f"[inventory_repo] No rows for SKU={sku}")
            return None
        result = _aggregate_rows(rows)
        print(f"[inventory_repo] Supabase returned {len(rows)} rows for SKU={sku}, total={result['total']}")
        return result
    except Exception as e:
        print(f"[inventory_repo] Error querying SKU={sku}: {e}")
        return None


def get_total_stock(sku: str) -> Optional[int]:
    """Get total stock quantity for a SKU."""
    stock = get_stock(sku)
    if stock is None:
        return None
    return stock.get("total", 0)
