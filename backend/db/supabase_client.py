"""
Supabase Data API client for read operations.

Uses the anon key for public read access via PostgREST.
Loads credentials from backend/.env automatically.
"""
import os
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load .env from backend folder (search upward from this file)
_this_dir = Path(__file__).resolve().parent
_backend_env = _this_dir.parent / ".env"
if _backend_env.exists():
    load_dotenv(_backend_env)
    print(f"[supabase_client] Loaded .env from: {_backend_env}")
else:
    load_dotenv()  # fallback to default search
    print("[supabase_client] Using default dotenv search")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().strip('"')
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip().strip('"')
FEATURE_SUPABASE_READ = os.getenv("FEATURE_SUPABASE_READ", "false").lower() == "true"

print(f"[supabase_client] URL set: {bool(SUPABASE_URL)}, ANON_KEY present: {bool(SUPABASE_ANON_KEY)}, Feature enabled: {FEATURE_SUPABASE_READ}")


def _get_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def _build_url(table: str) -> str:
    base = SUPABASE_URL.rstrip("/")
    return f"{base}/rest/v1/{table}"


def is_enabled() -> bool:
    """Check if Supabase reads are enabled and configured."""
    return FEATURE_SUPABASE_READ and bool(SUPABASE_URL) and bool(SUPABASE_ANON_KEY)


def select(
    table: str,
    params: Optional[str] = None,
    columns: str = "*",
    timeout: int = 10
) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query against a Supabase table.
    
    Args:
        table: Table name (e.g., 'inventory')
        params: PostgREST filter string (e.g., 'sku=eq.SKU000001')
        columns: Columns to select (default '*')
        timeout: Request timeout in seconds
    
    Returns:
        List of row dictionaries
    
    Raises:
        Exception on HTTP or network errors
    """
    url = _build_url(table)
    qs = f"?select={columns}"
    if params:
        qs += "&" + params
    
    full_url = url + qs
    
    try:
        resp = requests.get(full_url, headers=_get_headers(), timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", "N/A")
        body = getattr(e.response, "text", str(e))[:200]
        print(f"[supabase_client] HTTPError {status} on {table}: {body}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"[supabase_client] RequestException on {table}: {e}")
        raise


def select_one(
    table: str,
    params: Optional[str] = None,
    columns: str = "*"
) -> Optional[Dict[str, Any]]:
    """Select a single row (returns first match or None)."""
    rows = select(table, params=params, columns=columns)
    return rows[0] if rows else None
