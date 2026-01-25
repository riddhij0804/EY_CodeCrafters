"""
Customers repository: reads customers from Supabase.

Expects a 'customers' table with columns matching customers.csv
"""
import pandas as pd
from typing import Optional, Dict, Any
from ..supabase_client import select, is_enabled


def get_all_customers() -> Optional[pd.DataFrame]:
    """
    Get all customers from Supabase as a DataFrame.
    
    Returns:
        DataFrame with all customers, or None on error/disabled
    """
    if not is_enabled():
        return None
    
    try:
        rows = select("customers")
        if not rows:
            print("[customers_repo] No customers found in Supabase")
            return None
        
        df = pd.DataFrame(rows)
        print(f"[customers_repo] Loaded {len(df)} customers from Supabase")
        return df
    except Exception as e:
        print(f"[customers_repo] Error loading customers: {e}")
        return None


def get_customer_by_id(customer_id: int) -> Optional[Dict[str, Any]]:
    """Get a single customer by ID."""
    if not is_enabled():
        return None
    
    try:
        rows = select("customers", params=f"customer_id=eq.{customer_id}")
        return rows[0] if rows else None
    except Exception as e:
        print(f"[customers_repo] Error fetching customer_id={customer_id}: {e}")
        return None


def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Get a customer by phone number."""
    if not is_enabled():
        return None
    
    try:
        # Try exact match first
        rows = select("customers", params=f"phone_number=eq.{phone}")
        if rows:
            return rows[0]
        
        # Try with phone_number containing the digits
        rows = select("customers", params=f"phone_number=like.*{phone}*")
        return rows[0] if rows else None
    except Exception as e:
        print(f"[customers_repo] Error fetching phone={phone}: {e}")
        return None
