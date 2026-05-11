VHR_FIELD_CATALOG_SUGGESTED = [
    # --- Auction / Announcements / Notes ---
    {"key": "caution_notes",      "label": "Caution Notes",      "data_type": "TEXT",   "group": "auction", "help_text": "Major cautions/fail notes shown by auction", "options": {}},
    {"key": "announcements",      "label": "Announcements",      "data_type": "TEXT",   "group": "auction", "help_text": "Auction announcements / disclosures",        "options": {}},
    {"key": "buyer_notes",        "label": "Buyer Notes",        "data_type": "TEXT",   "group": "auction", "help_text": "Internal or buyer-facing notes",              "options": {}},

    # --- Reports (AutoCheck / Carfax) ---
    {"key": "autocheck_owners_count",        "label": "AutoCheck Owners",   "data_type": "NUMBER", "group": "reports", "help_text": "", "options": {"min": 0}},
    {"key": "autocheck_accidents_count",     "label": "AutoCheck Accidents","data_type": "NUMBER", "group": "reports", "help_text": "", "options": {"min": 0}},
    {"key": "autocheck_recalls_count",       "label": "AutoCheck Recalls",  "data_type": "NUMBER", "group": "reports", "help_text": "", "options": {"min": 0}},
    {"key": "autocheck_report_url",          "label": "AutoCheck Report URL","data_type": "TEXT",  "group": "reports", "help_text": "Link to report", "options": {}},

    {"key": "carfax_owners_count",           "label": "Carfax Owners",      "data_type": "NUMBER", "group": "reports", "help_text": "", "options": {"min": 0}},
    {"key": "carfax_accidents_count",        "label": "Carfax Accidents",   "data_type": "NUMBER", "group": "reports", "help_text": "", "options": {"min": 0}},
    {"key": "carfax_service_records_count",  "label": "Carfax Service Records","data_type": "NUMBER", "group": "reports", "help_text": "", "options": {"min": 0}},
    {"key": "carfax_report_url",             "label": "Carfax Report URL",  "data_type": "TEXT",   "group": "reports", "help_text": "Link to report", "options": {}},

    # --- Structural / Condition flags ---
    {"key": "structural_damage_flag", "label": "Structural Damage", "data_type": "BOOL", "group": "condition", "help_text": "True if structural damage present", "options": {}},
    {"key": "structural_damage_desc", "label": "Structural Damage Description", "data_type": "TEXT", "group": "condition", "help_text": "Details (e.g., rail kinked)", "options": {}},

    # --- Title status (example ENUM with choices) ---
    {
        "key": "title_status",
        "label": "Title Status",
        "data_type": "ENUM",
        "group": "paperwork",
        "help_text": "Declared title status",
        "options": {
            "choices": [
                {"value": "CLEAN",        "label": "Clean"},
                {"value": "REBUILT",      "label": "Rebuilt"},
                {"value": "SALVAGE",      "label": "Salvage"},
                {"value": "LIEN",         "label": "Lien"},
                {"value": "OTHER",        "label": "Other"},
            ]
        }
    },
]
