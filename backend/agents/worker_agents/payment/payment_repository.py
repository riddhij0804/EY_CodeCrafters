"""Utilities for persisting payment records to the shared CSV dataset."""

from __future__ import annotations

import csv
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable

BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import supabase_client  # type: ignore

logger = logging.getLogger(__name__)

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

_NUMERIC_FIELDS = {"amount_rupees", "discount_applied", "gst"}
_SUPABASE_TABLE = "payments"
_PAYMENT_ID_PATTERN = re.compile(r"^PAY\d{6}$")


def _load_existing_rows() -> Dict[str, Dict[str, str]]:
    """Return existing payment rows keyed by payment_id."""
    if not PAYMENTS_FILE.exists():
        return {}

    with PAYMENTS_FILE.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return {row["payment_id"]: row for row in reader if row.get("payment_id")}


def _is_valid_payment_id(payment_id: str | None) -> bool:
    return bool(payment_id) and bool(_PAYMENT_ID_PATTERN.match(payment_id))


def _generate_next_payment_id(rows: Dict[str, Dict[str, str]]) -> str:
    max_seq = 0
    for payment_id in rows.keys():
        match = _PAYMENT_ID_PATTERN.match(payment_id)
        if match:
            max_seq = max(max_seq, int(payment_id[3:]))
    next_seq = max_seq + 1
    return f"PAY{next_seq:06d}"


def generate_next_payment_id() -> str:
    with _WRITE_LOCK:
        rows = _load_existing_rows()
        return _generate_next_payment_id(rows)


def upsert_payment_record(record: Dict[str, str]) -> str:
    """Insert or update a payment entry in payments.csv in a threadsafe way.

    Returns the payment_id (generated if necessary).
    """
    payload = record.copy()
    payload.setdefault("created_at", datetime.utcnow().isoformat())

    with _WRITE_LOCK:
        rows = _load_existing_rows()
        if not _is_valid_payment_id(payload.get("payment_id")):
            payload["payment_id"] = _generate_next_payment_id(rows)

        rows[payload["payment_id"]] = {field: payload.get(field, "") for field in FIELDNAMES}

        PAYMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PAYMENTS_FILE.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows.values())

    _sync_to_supabase(payload)
    return payload["payment_id"]


def _prepare_supabase_payload(record: Dict[str, str]) -> Dict[str, object]:
    supabase_payload: Dict[str, object] = {}
    for field in FIELDNAMES:
        value = record.get(field)
        if value in ("", None):
            supabase_payload[field] = None
            continue

        if field in _NUMERIC_FIELDS:
            try:
                supabase_payload[field] = float(value)
            except (TypeError, ValueError):
                supabase_payload[field] = None
        else:
            supabase_payload[field] = value

    supabase_payload.setdefault("created_at", record.get("created_at"))
    supabase_payload.setdefault("status", record.get("status", "success"))
    return supabase_payload

def _ensure_idempotency(idempotency_key: str) -> None:
    existing = supabase_client.select_one(
        "idempotency",
        params=f"idempotency_key=eq.{idempotency_key}",
    )

    if not existing:
        supabase_client.upsert(
            "idempotency",
            {
                "idempotency_key": idempotency_key,
                "created_at": datetime.utcnow().isoformat(),
            },
            conflict_column="idempotency_key",
        )

def _sync_to_supabase(record: Dict[str, str]) -> None:
    if not supabase_client.is_write_enabled():
        return

    payload = _prepare_supabase_payload(record)
    try:
        # 1️⃣ Ensure idempotency exists FIRST
        _ensure_idempotency(payload["idempotency_key"])
        # 2️⃣ Insert payment (FK now valid)
        supabase_client.upsert(
            "payments",
            payload,
            conflict_column="payment_id",
        )
        # 3️⃣ Optionally store result
        supabase_client.update(
            "idempotency",
            {
                "result": {
                    "payment_id": payload["payment_id"],
                    "order_id": payload["order_id"],
                    "status": payload["status"],
                    "amount": payload["amount_rupees"],
                }
            },
            params=f"idempotency_key=eq.{payload['idempotency_key']}",
        )
        logger.info("[payment_repository] Synced payment %s to Supabase", record.get("payment_id"))
    except Exception as exc:  # broad to prevent payment flow failures
        logger.warning(
            "[payment_repository] Failed to sync payment %s to Supabase: %s",
            record.get("payment_id"),
            exc,
        )
