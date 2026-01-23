"""Utilities for persisting payment records to the shared CSV dataset."""

from __future__ import annotations

import csv
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
PAYMENTS_FILE = DATA_DIR / "payments.csv"
FIELDNAMES: Iterable[str] = (
    "payment_id",
    "order_id",
    "status",
    "amount_rupees",
    "discount_applied",
    "gst",
    "method",
    "gateway_ref",
    "idempotency_key",
    "created_at",
)

_WRITE_LOCK = Lock()


def _load_existing_rows() -> Dict[str, Dict[str, str]]:
    """Return existing payment rows keyed by payment_id."""
    if not PAYMENTS_FILE.exists():
        return {}

    with PAYMENTS_FILE.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return {row["payment_id"]: row for row in reader if row.get("payment_id")}


def upsert_payment_record(record: Dict[str, str]) -> None:
    """Insert or update a payment entry in payments.csv in a threadsafe way."""
    if "payment_id" not in record or not record["payment_id"]:
        raise ValueError("record must include a non-empty payment_id")

    with _WRITE_LOCK:
        rows = _load_existing_rows()
        rows[record["payment_id"]] = {field: record.get(field, "") for field in FIELDNAMES}

        PAYMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PAYMENTS_FILE.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows.values())
