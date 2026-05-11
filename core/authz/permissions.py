#permissions.py
from __future__ import annotations
class Permissions:
    VIEW_COMPANY = "view_company"
    MANAGE_COMPANY = "manage_company"

    VIEW_BILLING = "view_billing"
    MANAGE_BILLING = "manage_billing"
    
    VIEW_OWN_DEALERSHIPS = "view_own_dealerships"
    VIEW_ALL_DEALERSHIPS = "view_all_dealerships"
    VIEW_DEALERSHIP = "view_dealership"
    EDIT_DEALERSHIP = "edit_dealership"
    CREATE_DEALERSHIP = "create_dealership"
    DELETE_DEALERSHIP = "delete_dealership"

    VIEW_STAFF = "view_staff"
    MANAGE_STAFF = "manage_staff"
    
    VIEW_INVITES = "view_invites"
    INVITE_STAFF = "invite_staff"
    INVITE_VENDORS = "invite_vendors"
    MANAGE_INVITES = "manage_invites"

    VIEW_INVENTORY = "view_inventory"
    MANAGE_INVENTORY = "manage_inventory"
    IMPORT_VEHICLES = "import_vehicles"
    DELETE_VEHICLES = "delete_vehicles"

    VIEW_VHR = "view_vhr"
    MANAGE_VHR = "manage_vhr"

    VIEW_INSPECTIONS = "view_inspections"
    MANAGE_INSPECTIONS = "manage_inspections"
    ASSIGN_INSPECTORS = "assign_inspectors"

    VIEW_HAMMER = "view_hammer"
    MANAGE_HAMMER = "manage_hammer"

    VIEW_BUYING = "view_buying"
    MANAGE_BUYING = "manage_buying"

    VIEW_RECON = "view_recon"
    MANAGE_RECON = "manage_recon"
    ASSIGN_RECON_WORK = "assign_recon_work"

    VIEW_VENDOR_WORK = "view_vendor_work"
    MANAGE_VENDOR_WORK = "manage_vendor_work"
    UPLOAD_VENDOR_ATTACHMENTS = "upload_vendor_attachments"

    VIEW_NOTIFICATIONS = "view_notifications"
    MANAGE_NOTIFICATION_PREFERENCES = "manage_notification_preferences"

    VIEW_AUDIT_LOGS = "view_audit_logs"

    @classmethod
    def all(cls) -> set[str]:
        return {
            value
            for key, value in cls.__dict__.items()
            if key.isupper() and isinstance(value, str)
        }