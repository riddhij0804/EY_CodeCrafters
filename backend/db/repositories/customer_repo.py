"""Unified customer repository bridging Supabase and local CSV storage.

Provides read/write helpers with optional Supabase integration while keeping a
CSV mirror in sync so the rest of the stack can consume customer data even when
Supabase is unavailable.
"""
from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional

try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover - pandas is optional in some runtimes
    pd = None

try:
    from .. import supabase_client  # type: ignore
except Exception:  # pragma: no cover - fallback when Supabase client unavailable
    supabase_client = None

LOGGER = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.csv"
FIELDNAMES: Iterable[str] = (
    "customer_id",
    "name",
    "age",
    "gender",
    "phone_number",
    "city",
    "building_name",
    "address_landmark",
    "loyalty_tier",
    "loyalty_points",
    "device_preference",
    "total_spend",
    "items_purchased",
    "average_rating",
    "days_since_last_purchase",
    "satisfaction",
    "purchase_history",
)

_DEFAULT_VALUES = {
    "loyalty_tier": "Bronze",
    "loyalty_points": "0",
    "device_preference": "mobile",
    "total_spend": "0",
    "items_purchased": "0",
    "average_rating": "0",
    "days_since_last_purchase": "",
    "satisfaction": "New",
    "purchase_history": "[]",
    "building_name": "",
    "address_landmark": "",
}

_WRITE_LOCK = Lock()


def _supabase_available() -> bool:
    return supabase_client is not None


def _supabase_enabled() -> bool:
    return _supabase_available() and bool(supabase_client.is_enabled())


def _supabase_write_enabled() -> bool:
    return _supabase_available() and bool(supabase_client.is_write_enabled())


def _generate_guest_name(phone_digits: str) -> str:
    suffix = phone_digits[-4:] if phone_digits else "Guest"
    return f"Guest {suffix}"


def _coerce_purchase_history(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return []


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_dataframe(rows: List[Dict[str, Any]]) -> Optional["pd.DataFrame"]:
    if pd is None:
        LOGGER.warning("pandas not available; returning None instead of DataFrame")
        return None
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _sanitize_address(address: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not isinstance(address, dict):
        return {}

    cleaned: Dict[str, str] = {}
    for source_key, target_key in (
        ("city", "city"),
        ("landmark", "landmark"),
        ("address_landmark", "landmark"),
        ("building", "building"),
        ("building_name", "building"),
    ):
        value = address.get(source_key)
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            if target_key == "building" and "building" in cleaned and source_key != target_key:
                continue
            if target_key == "landmark" and "landmark" in cleaned and source_key != target_key:
                continue
            cleaned[target_key] = normalized
    return cleaned


def _prepare_address_updates(address: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cleaned = _sanitize_address(address)
    if not cleaned:
        return {}

    updates: Dict[str, Any] = {}

    city_value = cleaned.get("city")
    if city_value:
        updates["city"] = city_value

    building_value = cleaned.get("building")
    if building_value:
        updates["building_name"] = building_value

    landmark_value = cleaned.get("landmark")
    if landmark_value:
        updates["address_landmark"] = landmark_value

    return updates


def _sync_csv_from_supabase(customer: Dict[str, Any]) -> None:
    if not customer:
        return

    payload: Dict[str, Any] = {
        "customer_id": customer.get("customer_id"),
        "name": customer.get("name"),
        "phone_number": customer.get("phone_number"),
        "city": customer.get("city"),
        "building_name": customer.get("building_name"),
        "address_landmark": customer.get("address_landmark"),
        "loyalty_tier": customer.get("loyalty_tier"),
        "loyalty_points": customer.get("loyalty_points"),
        "total_spend": customer.get("total_spend"),
        "items_purchased": customer.get("items_purchased"),
        "purchase_history": json.dumps(customer.get("purchase_history", [])),
    }
    ensure_customer({k: v for k, v in payload.items() if v is not None})


def _normalize_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    return "".join(ch for ch in str(phone) if ch.isdigit())


def _supabase_select(table: str, params: Optional[str] = None, columns: str = "*") -> List[Dict[str, Any]]:
    if not _supabase_enabled():
        return []
    try:
        return supabase_client.select(table, params=params, columns=columns)
    except Exception as exc:
        LOGGER.warning("Supabase select failed for %s: %s", table, exc)
        return []


def _supabase_select_one(table: str, params: Optional[str] = None) -> Optional[Dict[str, Any]]:
    rows = _supabase_select(table, params=params)
    return rows[0] if rows else None


def _supabase_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    if not phone:
        return None
    normalized = _normalize_phone(phone)
    equality_candidates = []
    if phone:
        equality_candidates.append(phone)
    if normalized and normalized != phone:
        equality_candidates.append(normalized)

    for candidate in equality_candidates:
        record = _supabase_select_one("customers", params=f"phone_number=eq.{candidate}")
        if record:
            return record

    # Fallback to partial match when formatting differences prevent equality matches.
    like_candidates = []
    if normalized:
        like_candidates.append(normalized)
    elif phone:
        like_candidates.append(phone)

    for candidate in like_candidates:
        record = _supabase_select_one("customers", params=f"phone_number=like.*{candidate}*")
        if record:
            return record
    return None


def _supabase_next_customer_id() -> int:
    default_start = 100000
    rows = _supabase_select(
        "customers",
        params="order=customer_id.desc&limit=1",
        columns="customer_id",
    )
    if not rows:
        return default_start
    latest = rows[0].get("customer_id")
    try:
        return int(latest) + 1
    except (TypeError, ValueError):
        return default_start


def _stringify(field: str, value: Optional[str]) -> str:
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        value = str(value)
    else:
        value = str(value).strip()

    if field == "phone_number":
        normalized = _normalize_phone(value)
        return normalized or value

    return value


def _load_rows() -> List[Dict[str, str]]:
    if not CUSTOMERS_FILE.exists():
        return []

    with CUSTOMERS_FILE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _merge_row(base: Dict[str, str], updates: Dict[str, str]) -> Dict[str, str]:
    merged = dict(base)
    for field in FIELDNAMES:
        if field in updates and updates[field] is not None:
            merged[field] = _stringify(field, updates[field])
    return merged


def _materialize_record(payload: Dict[str, str]) -> Dict[str, str]:
    result = {field: _stringify(field, payload.get(field, "")) for field in FIELDNAMES}
    for key, default_value in _DEFAULT_VALUES.items():
        if not result.get(key):
            result[key] = default_value
    return result


def _next_customer_id(rows: Optional[List[Dict[str, str]]] = None) -> str:
    if rows is None:
        rows = _load_rows()

    max_id = 0
    for row in rows:
        raw = (row.get("customer_id") or "").strip()
        try:
            value = int(raw)
            if value > max_id:
                max_id = value
        except ValueError:
            continue

    next_id = max(max_id, 100) + 1
    return str(next_id)


def find_customer_by_id(customer_id: str | int) -> Optional[Dict[str, str]]:
    target = _stringify("customer_id", customer_id)
    for row in _load_rows():
        if row.get("customer_id") == target:
            return row
    return None


def find_customer_by_phone(phone: str) -> Optional[Dict[str, str]]:
    target = _normalize_phone(phone)
    for row in _load_rows():
        if _normalize_phone(row.get("phone_number")) == target:
            return row
    return None


def upsert_customer(record: Dict[str, object]) -> Dict[str, str]:
    incoming: Dict[str, object] = {}
    for field in FIELDNAMES:
        if field in record and record[field] is not None:
            incoming[field] = record[field]

    with _WRITE_LOCK:
        rows = _load_rows()

        customer_id = incoming.get("customer_id")
        if not customer_id or str(customer_id).strip() == "":
            customer_id = _next_customer_id(rows)

        customer_id = _stringify("customer_id", customer_id)
        incoming["customer_id"] = customer_id

        target_index: Optional[int] = None
        for index, row in enumerate(rows):
            if row.get("customer_id") == customer_id:
                target_index = index
                break

        if target_index is not None:
            merged = _merge_row(rows[target_index], incoming)
            rows[target_index] = merged
            result = merged
            LOGGER.info("Updated customer %s", customer_id)
        else:
            new_record = _materialize_record(incoming)
            rows.append(new_record)
            result = new_record
            LOGGER.info("Added new customer %s", customer_id)

        CUSTOMERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CUSTOMERS_FILE.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    return result


def ensure_customer(record: Dict[str, object]) -> Dict[str, str]:
    """Ensure a customer exists, preferring lookup by id, then phone."""
    customer_id = record.get("customer_id")
    phone = record.get("phone_number")

    existing: Optional[Dict[str, str]] = None

    if customer_id:
        existing = find_customer_by_id(customer_id)

    if not existing and phone:
        existing = find_customer_by_phone(phone)

    if existing:
        updates = {}
        for field in ("name", "age", "gender", "phone_number", "city"):
            if record.get(field) not in (None, ""):
                updates[field] = record[field]
        updates["customer_id"] = existing.get("customer_id") or customer_id
        return upsert_customer(updates)

    if not phone and not customer_id:
        raise ValueError("phone_number is required to create a customer")

    prepared = dict(record)
    if phone:
        prepared["phone_number"] = _normalize_phone(phone) or phone
    return upsert_customer(prepared)


def get_all_customers() -> Optional["pd.DataFrame"]:
    """Return customers as a DataFrame using Supabase when available."""
    rows: List[Dict[str, Any]] = []

    if _supabase_enabled():
        rows = _supabase_select("customers")
        if rows:
            return _to_dataframe(rows)

    rows = _load_rows()
    return _to_dataframe(rows)


def get_customer_by_id(customer_id: str | int) -> Optional[Dict[str, Any]]:
    """Fetch a customer by id, preferring Supabase data."""
    if _supabase_enabled():
        record = _supabase_select_one("customers", params=f"customer_id=eq.{customer_id}")
        if record:
            return record
    return find_customer_by_id(customer_id)


def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Fetch a customer by phone, preferring Supabase data."""
    if _supabase_enabled():
        record = _supabase_customer_by_phone(phone)
        if record:
            return record
    return find_customer_by_phone(phone)


def ensure_customer_record(
    phone: str,
    *,
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    sync_csv: bool = True,
    address: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Ensure a Supabase customer exists for the provided phone number."""

    if not phone:
        return None

    attributes = dict(attributes or {})
    normalized_phone = _normalize_phone(phone)
    address_updates = _prepare_address_updates(address)

    if _supabase_enabled():
        existing = _supabase_customer_by_phone(phone)
        if existing:
            update_payload: Dict[str, Any] = {}

            if name and name.strip() and name != existing.get("name"):
                update_payload["name"] = name.strip()

            if attributes:
                for key, value in attributes.items():
                    if value not in (None, "") and existing.get(key) != value:
                        update_payload[key] = value

            if address_updates:
                for key, value in address_updates.items():
                    if value not in (None, "") and existing.get(key) != value:
                        update_payload[key] = value

            if update_payload and _supabase_write_enabled():
                try:
                    payload: Dict[str, Any] = {
                        "phone_number": existing.get("phone_number") or normalized_phone or phone,
                    }
                    if existing.get("customer_id"):
                        payload["customer_id"] = existing["customer_id"]
                    payload.update(update_payload)

                    LOGGER.info(
                        "Upserting Supabase customer %s with payload: %s",
                        phone,
                        payload,
                    )

                    response = supabase_client.upsert(
                        "customers",
                        payload,
                        conflict_column="customer_id" if existing.get("customer_id") else "phone_number",
                    )

                    if response:
                        existing.update(response[0])
                    else:
                        existing.update(payload)
                except Exception as exc:
                    LOGGER.warning(
                        "Failed to upsert Supabase customer %s with new attributes: %s",
                        phone,
                        exc,
                    )
                else:
                    LOGGER.info("Supabase customer %s upserted successfully.", phone)
            else:
                LOGGER.debug(
                    "No Supabase updates required for customer %s (write_enabled=%s)",
                    phone,
                    _supabase_write_enabled(),
                )

            if sync_csv:
                _sync_csv_from_supabase(existing)
            return existing

        if not _supabase_write_enabled():
            LOGGER.debug("Supabase write disabled; falling back to CSV ensure for %s", phone)
            if sync_csv:
                csv_payload = dict(attributes)
                csv_payload.setdefault("phone_number", phone)
                if name:
                    csv_payload.setdefault("name", name)
                return ensure_customer(csv_payload)
            return None

        new_customer_id = _supabase_next_customer_id()
        base_phone = normalized_phone or phone

        payload: Dict[str, Any] = {
            "customer_id": new_customer_id,
            "phone_number": base_phone,
            "name": name or attributes.get("name") or _generate_guest_name(base_phone),
            "age": attributes.get("age"),
            "gender": attributes.get("gender"),
            "city": attributes.get("city"),
            "loyalty_tier": attributes.get("loyalty_tier", "Bronze"),
            "loyalty_points": _coerce_int(attributes.get("loyalty_points"), 0),
            "device_preference": attributes.get("device_preference", "mobile"),
            "total_spend": _coerce_float(attributes.get("total_spend"), 0.0),
            "items_purchased": _coerce_int(attributes.get("items_purchased"), 0),
            "average_rating": _coerce_float(attributes.get("average_rating"), 0.0),
            "days_since_last_purchase": attributes.get("days_since_last_purchase"),
            "satisfaction": attributes.get("satisfaction", "New"),
            "purchase_history": _coerce_purchase_history(attributes.get("purchase_history")),
        }

        for key, value in attributes.items():
            if key not in payload:
                payload[key] = value

        if address_updates:
            payload.update(address_updates)

        try:
            result = supabase_client.upsert("customers", payload, conflict_column="customer_id")
            customer = result[0] if result else payload
        except Exception as exc:
            LOGGER.warning("Failed to upsert Supabase customer %s: %s", phone, exc)
            if sync_csv:
                csv_payload = dict(attributes)
                csv_payload.setdefault("phone_number", phone)
                if name:
                    csv_payload.setdefault("name", name)
                return ensure_customer(csv_payload)
            return None

        if sync_csv:
            _sync_csv_from_supabase(customer)
        return customer

    if sync_csv:
        csv_payload = dict(attributes)
        csv_payload.setdefault("phone_number", phone)
        if name:
            csv_payload.setdefault("name", name)
        if address_updates:
            csv_payload.update({k: v for k, v in address_updates.items() if isinstance(v, str)})
        return ensure_customer(csv_payload)
    return None
