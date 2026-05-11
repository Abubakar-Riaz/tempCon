# notifications/constants.py

class NotificationTypes:
    VEHICLE_CREATED = "vehicle.created"
    VEHICLE_STATUS_CHANGED = "vehicle.status_changed"
    VEHICLE_ASSIGNED = "vehicle.assigned"

    INSPECTION_ASSIGNED = "inspection.assigned"
    INSPECTION_UPDATED = "inspection.updated"
    INSPECTION_COMPLETED = "inspection.completed"

    HAMMER_UPDATED = "hammer.updated"
    HAMMER_FINALIZED = "hammer.finalized"

    BUYING_DECISION_MADE = "buying.decision_made"

    RECON_ASSIGNED = "recon.assigned"
    RECON_WORK_ASSIGNED = "recon.work_assigned"
    RECON_WORK_COMPLETED = "recon.work_completed"
    RECON_FAILED = "recon.failed"
    RECON_COMPLETED = "recon.completed"

    VENDOR_WORK_ASSIGNED = "vendor.work_assigned"
    VENDOR_WORK_UPDATED = "vendor.work_updated"

    BILLING_ALERT = "billing.alert"
    SYSTEM_ALERT = "system.alert"

    @classmethod
    def all(cls) -> set[str]:
        return {
            value
            for key, value in cls.__dict__.items()
            if key.isupper() and isinstance(value, str)
        }


class NotificationCategories:
    VEHICLES = "vehicles"
    INSPECTIONS = "inspections"
    HAMMER = "hammer"
    BUYING = "buying"
    RECON = "recon"
    VENDORS = "vendors"
    BILLING = "billing"
    SYSTEM = "system"

    @classmethod
    def all(cls) -> set[str]:
        return {
            value
            for key, value in cls.__dict__.items()
            if key.isupper() and isinstance(value, str)
        }


class NotificationPriorities:
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def all(cls) -> set[str]:
        return {
            value
            for key, value in cls.__dict__.items()
            if key.isupper() and isinstance(value, str)
        }


class NotificationEntityTypes:
    VEHICLE = "vehicle"
    INSPECTION = "inspection"
    INSPECTION_ITEM = "inspection_item"
    HAMMER_SESSION = "hammer_session"
    BUYING_DECISION = "buying_decision"
    RECON_CASE = "recon_case"
    WORK_ITEM = "work_item"
    USER = "user"
    SYSTEM = "system"

    @classmethod
    def all(cls) -> set[str]:
        return {
            value
            for key, value in cls.__dict__.items()
            if key.isupper() and isinstance(value, str)
        }


class NotificationChannels:
    IN_APP = "in_app"
    WEBSOCKET = "websocket"
    EMAIL = "email"
    PUSH = "push"


class NotificationDeliveryStatuses:
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"