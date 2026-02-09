"""Compatibility shim delegating to the unified customer_repo module."""

from . import customer_repo as _customer_repo

find_customer_by_id = _customer_repo.find_customer_by_id
find_customer_by_phone = _customer_repo.find_customer_by_phone
get_all_customers = _customer_repo.get_all_customers
get_customer_by_id = _customer_repo.get_customer_by_id
get_customer_by_phone = _customer_repo.get_customer_by_phone
ensure_customer = _customer_repo.ensure_customer
ensure_customer_record = _customer_repo.ensure_customer_record
upsert_customer = _customer_repo.upsert_customer

__all__ = [
    "find_customer_by_id",
    "find_customer_by_phone",
    "get_all_customers",
    "get_customer_by_id",
    "get_customer_by_phone",
    "ensure_customer",
    "ensure_customer_record",
    "upsert_customer",
]
