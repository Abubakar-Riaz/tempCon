# notifications/registry.py

from notifications.constants import (
    NotificationCategories,
    NotificationChannels,
    NotificationPriorities,
    NotificationTypes,
)


NOTIFICATION_CATEGORY_DEFAULTS = {
    NotificationCategories.VEHICLES: {
        "label": "Vehicles",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: False,
        },
    },
    NotificationCategories.INSPECTIONS: {
        "label": "Inspections",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: False,
        },
    },
    NotificationCategories.HAMMER: {
        "label": "Hammer",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: False,
        },
    },
    NotificationCategories.BUYING: {
        "label": "Buying",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: False,
        },
    },
    NotificationCategories.RECON: {
        "label": "Recon",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: False,
        },
    },
    NotificationCategories.VENDORS: {
        "label": "Vendors",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: True,
        },
    },
    NotificationCategories.BILLING: {
        "label": "Billing",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: True,
        },
    },
    NotificationCategories.SYSTEM: {
        "label": "System",
        "default_channels": {
            NotificationChannels.IN_APP: True,
            NotificationChannels.WEBSOCKET: True,
            NotificationChannels.EMAIL: True,
        },
    },
}


NOTIFICATION_TYPE_CONFIG = {
    NotificationTypes.VEHICLE_CREATED: {
        "category": NotificationCategories.VEHICLES,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.VEHICLE_STATUS_CHANGED: {
        "category": NotificationCategories.VEHICLES,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.VEHICLE_ASSIGNED: {
        "category": NotificationCategories.VEHICLES,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.INSPECTION_ASSIGNED: {
        "category": NotificationCategories.INSPECTIONS,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.INSPECTION_UPDATED: {
        "category": NotificationCategories.INSPECTIONS,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.INSPECTION_COMPLETED: {
        "category": NotificationCategories.INSPECTIONS,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.HAMMER_UPDATED: {
        "category": NotificationCategories.HAMMER,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.HAMMER_FINALIZED: {
        "category": NotificationCategories.HAMMER,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.BUYING_DECISION_MADE: {
        "category": NotificationCategories.BUYING,
        "default_priority": NotificationPriorities.HIGH,
    },
    NotificationTypes.RECON_ASSIGNED: {
        "category": NotificationCategories.RECON,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.RECON_WORK_ASSIGNED: {
        "category": NotificationCategories.RECON,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.RECON_WORK_COMPLETED: {
        "category": NotificationCategories.RECON,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.RECON_FAILED: {
        "category": NotificationCategories.RECON,
        "default_priority": NotificationPriorities.HIGH,
    },
    NotificationTypes.RECON_COMPLETED: {
        "category": NotificationCategories.RECON,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.VENDOR_WORK_ASSIGNED: {
        "category": NotificationCategories.VENDORS,
        "default_priority": NotificationPriorities.HIGH,
    },
    NotificationTypes.VENDOR_WORK_UPDATED: {
        "category": NotificationCategories.VENDORS,
        "default_priority": NotificationPriorities.NORMAL,
    },
    NotificationTypes.BILLING_ALERT: {
        "category": NotificationCategories.BILLING,
        "default_priority": NotificationPriorities.CRITICAL,
    },
    NotificationTypes.SYSTEM_ALERT: {
        "category": NotificationCategories.SYSTEM,
        "default_priority": NotificationPriorities.NORMAL,
    },
}


def get_notification_type_config(notification_type: str) -> dict:
    return NOTIFICATION_TYPE_CONFIG[notification_type]


def get_default_category_for_type(notification_type: str) -> str:
    return get_notification_type_config(notification_type)["category"]


def get_default_priority_for_type(notification_type: str) -> str:
    return get_notification_type_config(notification_type)["default_priority"]


def get_default_channels_for_category(category: str) -> dict:
    return NOTIFICATION_CATEGORY_DEFAULTS[category]["default_channels"]


def is_valid_notification_type(notification_type: str) -> bool:
    return notification_type in NOTIFICATION_TYPE_CONFIG


def is_valid_notification_category(category: str) -> bool:
    return category in NOTIFICATION_CATEGORY_DEFAULTS