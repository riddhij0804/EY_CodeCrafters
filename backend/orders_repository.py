"""Utilities for persisting order records to the shared CSV dataset."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, Any, List

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
ORDERS_FILE = DATA_DIR / "orders.csv"
FIELDNAMES: Iterable[str] = (
    "order_id",
    "customer_id",
    "items",
    "total_amount",
    "status",
    "created_at",
)

_WRITE_LOCK = Lock()


def _load_existing_rows() -> Dict[str, Dict[str, str]]:
    """Return existing order rows keyed by order_id."""
    if not ORDERS_FILE.exists():
        return {}

    with ORDERS_FILE.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return {row["order_id"]: row for row in reader if row.get("order_id")}


def upsert_order_record(record: Dict[str, Any]) -> None:
    """Insert or update an order entry in orders.csv in a threadsafe way."""
    if "order_id" not in record or not record["order_id"]:
        raise ValueError("record must include a non-empty order_id")

    logger.info(f"📝 Upserting order: {record.get('order_id')}")
    
    # Ensure items is JSON string if it's a dict/list
    if isinstance(record.get("items"), (dict, list)):
        record["items"] = json.dumps(record["items"])
        logger.debug(f"   Serialized items to JSON")

    with _WRITE_LOCK:
        logger.debug(f"   Acquired write lock")
        rows = _load_existing_rows()
        logger.debug(f"   Loaded {len(rows)} existing rows")
        
        rows[record["order_id"]] = {field: str(record.get(field, "")) for field in FIELDNAMES}
        logger.debug(f"   Updated row for order_id")

        ORDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"   Ensured directory exists: {ORDERS_FILE.parent}")
        
        with ORDERS_FILE.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows.values())
            logger.info(f"✅ Written {len(rows)} orders to {ORDERS_FILE}")
