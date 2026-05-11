# authx/services/signup.py

from __future__ import annotations

import json

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Company, Dealership, DealershipMembership, DealershipRole, MembershipStatus, User
from authx.models import AuthProvider, UserProvider


def run_post_signup_jobs(*, user: User, company: Company, dealership: Dealership):
    """
    Placeholder for post-success signup work.

    Later:
    - send welcome email
    - create billing customer
    - seed default settings
    - enqueue onboarding jobs
    - notify internal systems
    """
    return None


@transaction.atomic
def complete_signup_from_challenge(*, challenge):
    user = challenge.user
    meta = json.loads(challenge.user_agent or "{}")

    company_name = (meta.get("company_name") or "").strip()

    if not user:
        raise ValueError("Missing signup user.")

    if not company_name:
        raise ValueError("Missing signup context.")

    try:
        company = Company.objects.create(
            name=company_name,
            created_by=user,
        )

        dealership = Dealership.objects.create(
            company=company,
            name=company_name,
            created_by=user,
            is_active=True,
            is_default=True,
        )

        membership = DealershipMembership.objects.create(
            user=user,
            company=company,
            dealership=dealership,
            role=DealershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            is_company_owner=True,
            is_default=True,
            joined_at=timezone.now(),
        )

        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])

        UserProvider.objects.get_or_create(
            user=user,
            provider=AuthProvider.PASSWORD,
        )

    except IntegrityError as exc:
        raise ValueError("Company name already exists.") from exc

    run_post_signup_jobs(
        user=user,
        company=company,
        dealership=dealership,
    )

    return user, company, dealership, membership