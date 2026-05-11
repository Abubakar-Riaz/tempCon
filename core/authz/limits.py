#core/authz/limits.py
from __future__ import annotations
class Limits:
    MAX_USERS = "max_users"
    MAX_DEALERSHIPS = "max_dealerships"

    MAX_VEHICLES_PER_MONTH = "max_vehicles_per_month"
    MAX_ACTIVE_VEHICLES = "max_active_vehicles"

    MAX_STORAGE_BYTES = "max_storage_bytes"
    MAX_ATTACHMENTS_PER_VEHICLE = "max_attachments_per_vehicle"

    MAX_VENDOR_USERS = "max_vendor_users"
    MAX_TRADES = "max_trades"

    @classmethod
    def all(cls) -> set[str]:
        return {
            value
            for key, value in cls.__dict__.items()
            if key.isupper() and isinstance(value, str)
        }