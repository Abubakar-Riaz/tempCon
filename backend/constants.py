# Base machine codes (keep these stable for FE error boundaries)
from inventory.models import FolderType, VehicleStatus


VALIDATION_ERROR = "VALIDATION_ERROR"
UNAUTHORIZED = "UNAUTHORIZED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
RATE_LIMITED = "RATE_LIMITED"
SERVER_ERROR = "SERVER_ERROR"

# Domain examples
OTP_INVALID = "OTP_INVALID"
OTP_EXPIRED = "OTP_EXPIRED"
OTP_MAX_ATTEMPTS = "OTP_MAX_ATTEMPTS"
ENTITLEMENT_MISSING = "ENTITLEMENT_MISSING"
PLAN_LIMIT_REACHED = "PLAN_LIMIT_REACHED"

USER_INACTIVE = "USER_INACTIVE"
USER_BLOCKED = "USER_BLOCKED"
NO_COMPANY_CONTEXT = "NO_COMPANY_CONTEXT"
NO_MEMBERSHIP = "NO_MEMBERSHIP"
SUBSCRIPTION_INACTIVE = "SUBSCRIPTION_INACTIVE"
ROLE_FORBIDDEN = "ROLE_FORBIDDEN"
PLAN_FORBIDDEN = "ENTITLEMENT_MISSING"
PLAN_LIMIT_REACHED = "PLAN_LIMIT_REACHED"


ACTIVE_SUB_STATUSES = {"active", "in_trial"}
ACTION_STAFF_INVITE = "staff.invite"
ACTION_DEALERSHIP_CREATE = "dealership.create"

ENT_STAFF_INVITE = "staff.invite"                 # BOOL (feature toggle)
ENT_STAFF_INVITE_LIMIT = "staff.invite.limit"     # INT (cap per window)
ENT_STAFF_INVITE_WINDOW = "staff.invite.window"   # STR in {"period","month","all_time"}  (DEFAULT "period")
ENT_DEALERSHIP_CREATE = "dealership.create"       # BOOL
ENT_DEALERSHIP_LIMIT = "dealership.limit"         # INT (cap)


ROLE_PERMS = {
    "COMPANY_ADMIN": {ACTION_STAFF_INVITE, ACTION_DEALERSHIP_CREATE},
    "LOCATION_ADMIN": {ACTION_STAFF_INVITE},
    "MANAGER": set(),
    "INSPECTOR": set(),
    "BUYER": set(),
    "RECON_MANAGER": set(),
    "VENDOR": set(),
}


# MAX SNAPSHOT SIZE (IN CHARACTERS) TO AVOID HUGE ROWS
MAX_SNAPSHOT_CHARS = 4000  # MOVE TO constants.py

# SENSITIVE KEYS TO REDACT ANYWHERE THEY APPEAR IN before/after
SENSITIVE_KEYS = {"password", "token", "otp", "secret", "authorization", "api_key", "refresh_token"}  # MOVE

# CAPTURE BODY/QUERY EXCERPTS? (SAFE DEFAULT: OFF)
CAPTURE_REQUEST_EXCERPTS = False   # MOVE
CAPTURE_RESPONSE_EXCERPTS = False  # MOVE
EXCERPT_MAX_CHARS = 1024           # MOVE

# OPTIONAL: ONLY WRITE WHEN THERE ARE QUEUED ENTRIES OR SECURITY EVENTS
# (SET TO True IF YOU WANT A "ONE ROW PER REQUEST" POLICY)
ALWAYS_WRITE_BASELINE_ENTRY = False  # MOVE



PLAN_BASIC = "BASIC"

# Subscription status mapping
SUB_IN_TRIAL = "IN_TRIAL"
SUB_ACTIVE = "ACTIVE"
SUB_PAST_DUE = "PAST_DUE"
SUB_CANCELED = "CANCELED"
SUB_PENDING_PAYMENT = "PENDING_PAYMENT"



CSV_HEADERS = [
    "Vin", "Run Number", "Auction House", "Sale", "Start Time",
    "Main Description", "Secondary Description", "Title", "Grade",
    "MMR", "Odometer", "Engine", "Transmission", "Exterior Color",
    "Interior Color", "Consignor", "Consignor E-mail", "Consignor Address",
    "Notes"
]

HEADER_MAP = {
    "vin": "vin",
    "run number": "run_number",
    "auction house": "auction_house",
    "sale": "auction_sale_lane",
    "start time": "auction_start_at",
    "main description": "main_description",
    "secondary description": "secondary_description",
    "title": "title_status",
    "grade": "condition_grade",
    "mmr": "mmr",
    "odometer": "mileage",
    "engine": "engine",
    "transmission": "transmission",
    "exterior color": "exterior_color",
    "interior color": "interior_color",
    "consignor": "consignor_name",
    "consignor e-mail": "consignor_email",
    "consignor address": "consignor_address",
    "notes": "auction_notes",
}



# -------- Phase graph & policy --------

SUCCESSOR = {
    VehicleStatus.VHR:        VehicleStatus.INSPECTION,
    VehicleStatus.INSPECTION: VehicleStatus.HAMMER,
    VehicleStatus.HAMMER:     VehicleStatus.BUYING,
    VehicleStatus.BUYING:     VehicleStatus.RECON,   
    VehicleStatus.RECON:      VehicleStatus.COMPLETE,
}

# Non-admin initiators allowed (admins bypass)
REQUIRED_ROLE_FOR_TRANSITION = {
    (VehicleStatus.VHR,        VehicleStatus.INSPECTION): "MANAGER",
    (VehicleStatus.INSPECTION, VehicleStatus.HAMMER):     "INSPECTOR",
    (VehicleStatus.HAMMER,     VehicleStatus.BUYING):     "MANAGER",
    (VehicleStatus.RECON,      VehicleStatus.COMPLETE):   "RECON_MANAGER",
}

# Who owns the destination phase (for assignment + auto-daily)
OWNER_ROLE_FOR_PHASE = {
    VehicleStatus.INSPECTION: "INSPECTOR",
    VehicleStatus.HAMMER:     "MANAGER",     
    VehicleStatus.BUYING:     "MANAGER",
    VehicleStatus.RECON:      "RECON_MANAGER",
    VehicleStatus.COMPLETE:   "RECON_MANAGER",
}

# Auto-daily folder type per phase
FOLDERTYPE_FOR_PHASE = {
    VehicleStatus.INSPECTION: FolderType.AUTO_INSPECTION_DAILY,
    VehicleStatus.HAMMER:     FolderType.AUTO_BUYING_DAILY, 
    VehicleStatus.BUYING:     FolderType.AUTO_BUYING_DAILY,
    VehicleStatus.RECON:      FolderType.AUTO_RECON_DAILY,
    VehicleStatus.COMPLETE:   FolderType.AUTO_RECON_DAILY,
    "VENDOR": FolderType.AUTO_VENDOR_DAILY,
}