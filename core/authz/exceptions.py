from rest_framework.exceptions import PermissionDenied, ValidationError


class MissingDealershipHeaderError(ValidationError):
    default_detail = "Missing required X-Dealership-Id header."
    default_code = "missing_dealership_header"


class InvalidDealershipError(PermissionDenied):
    default_detail = "Invalid dealership."
    default_code = "invalid_dealership"


class MembershipRequiredError(PermissionDenied):
    default_detail = "You do not have access to this dealership."
    default_code = "membership_required"


class FeatureNotAvailableError(PermissionDenied):
    default_detail = "This feature is not available on your current plan."
    default_code = "feature_not_available"


class LimitExceededError(PermissionDenied):
    default_detail = "Your plan limit has been reached."
    default_code = "limit_exceeded"