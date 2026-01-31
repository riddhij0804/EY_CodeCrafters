"""Helpers for working with backend/data/customers.csv.

Provides lightweight read/update utilities with basic locking so other
services can ensure a customer record exists when users log in.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional

LOGGER = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.csv"
FIELDNAMES: Iterable[str] = (
    "customer_id",
    "name",
    "age",
    "gender",
    "phone_number",
    "city",
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
}

_WRITE_LOCK = Lock()


def _normalize_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    return "".join(ch for ch in str(phone) if ch.isdigit())


def _stringify(field: str, value: Optional[str]) -> str:
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        # Keep integer formatting for ids / counts, avoid trailing .0
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
            new_record = _materialize_record(incoming)  # fill defaults for new customer
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

    # If we found an existing record, merge primary fields but do not drop data
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
