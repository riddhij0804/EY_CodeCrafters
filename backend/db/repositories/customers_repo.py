"""
Customers repository: reads customers from Supabase.

Expects a 'customers' table with columns matching customers.csv
"""
import logging
import pandas as pd
from typing import Optional, Dict, Any
from ..supabase_client import select, is_enabled, upsert, is_write_enabled


logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in str(phone) if ch.isdigit())


def _generate_guest_name(phone_digits: str) -> str:
    suffix = phone_digits[-4:] if phone_digits else "Guest"
    return f"Guest {suffix}"


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


def ensure_customer_record(
    phone: str,
    *,
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Ensure a Supabase customer exists for the provided phone number."""
    if not phone:
        return None

    if not is_enabled() or not is_write_enabled():
        logger.debug("[customers_repo] Supabase not fully enabled; skipping ensure_customer_record")
        return None

    normalized_phone = _normalize_phone(phone)

    existing = get_customer_by_phone(phone)
    if not existing and normalized_phone != phone:
        existing = get_customer_by_phone(normalized_phone)

    if existing:
        return existing

    try:
        latest = select(
            "customers",
            params="order=customer_id.desc&limit=1",
            columns="customer_id"
        )
        if latest:
            last_id = latest[0].get("customer_id")
            try:
                new_customer_id = int(last_id) + 1
            except (TypeError, ValueError):
                new_customer_id = 100000
        else:
            new_customer_id = 100000
    except Exception as exc:
        logger.warning("[customers_repo] Could not determine next customer id: %s", exc)
        new_customer_id = 100000

    phone_to_store = normalized_phone or str(phone)
    customer_payload: Dict[str, Any] = {
        "customer_id": new_customer_id,
        "phone_number": phone_to_store,
        "name": name or _generate_guest_name(phone_to_store),
        "age": None,
        "gender": None,
        "city": None,
        "loyalty_tier": "Bronze",
        "loyalty_points": 0,
        "device_preference": "mobile",
        "total_spend": 0,
        "items_purchased": 0,
        "average_rating": 0,
        "days_since_last_purchase": None,
        "satisfaction": "New",
        "purchase_history": [],
    }

    if attributes:
        customer_payload.update(attributes)

    try:
        result = upsert("customers", customer_payload, conflict_column="customer_id")
        if result:
            return result[0]
    except Exception as exc:
        logger.warning("[customers_repo] Failed to upsert customer %s: %s", phone_to_store, exc)
        return None

    return customer_payload
