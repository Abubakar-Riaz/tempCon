from __future__ import annotations

from core.authz.permissions import Permissions


ROLE_DEFAULT_PERMISSIONS: dict[str, set[str]] = {
    "admin": Permissions.all(),

    "manager": {
        Permissions.VIEW_COMPANY,

        Permissions.VIEW_OWN_DEALERSHIPS,
        Permissions.VIEW_DEALERSHIP,
        Permissions.EDIT_DEALERSHIP,

        Permissions.VIEW_STAFF,
        Permissions.MANAGE_STAFF,

        Permissions.VIEW_INVITES,
        Permissions.INVITE_STAFF,
        Permissions.INVITE_VENDORS,
        Permissions.MANAGE_INVITES,

        Permissions.VIEW_INVENTORY,
        Permissions.MANAGE_INVENTORY,
        Permissions.IMPORT_VEHICLES,

        Permissions.VIEW_VHR,
        Permissions.MANAGE_VHR,

        Permissions.VIEW_INSPECTIONS,
        Permissions.MANAGE_INSPECTIONS,
        Permissions.ASSIGN_INSPECTORS,

        Permissions.VIEW_HAMMER,
        Permissions.MANAGE_HAMMER,

        Permissions.VIEW_BUYING,
        Permissions.MANAGE_BUYING,

        Permissions.VIEW_RECON,
        Permissions.MANAGE_RECON,
        Permissions.ASSIGN_RECON_WORK,

        Permissions.VIEW_VENDOR_WORK,
        Permissions.MANAGE_VENDOR_WORK,

        Permissions.VIEW_NOTIFICATIONS,
        Permissions.MANAGE_NOTIFICATION_PREFERENCES,
    },

    "recon_manager": {
        Permissions.VIEW_OWN_DEALERSHIPS,
        Permissions.VIEW_DEALERSHIP,

        Permissions.VIEW_INVENTORY,

        Permissions.VIEW_INSPECTIONS,
        Permissions.VIEW_HAMMER,

        Permissions.VIEW_RECON,
        Permissions.MANAGE_RECON,
        Permissions.ASSIGN_RECON_WORK,

        Permissions.VIEW_VENDOR_WORK,
        Permissions.MANAGE_VENDOR_WORK,

        Permissions.VIEW_NOTIFICATIONS,
    },

    "inspector": {
        Permissions.VIEW_OWN_DEALERSHIPS,
        Permissions.VIEW_DEALERSHIP,

        Permissions.VIEW_INVENTORY,

        Permissions.VIEW_VHR,

        Permissions.VIEW_INSPECTIONS,
        Permissions.MANAGE_INSPECTIONS,

        Permissions.VIEW_HAMMER,

        Permissions.VIEW_NOTIFICATIONS,
    },

    "vendor": {
        Permissions.VIEW_DEALERSHIP,

        Permissions.VIEW_VENDOR_WORK,
        Permissions.MANAGE_VENDOR_WORK,
        Permissions.UPLOAD_VENDOR_ATTACHMENTS,

        Permissions.VIEW_NOTIFICATIONS,
    },
}