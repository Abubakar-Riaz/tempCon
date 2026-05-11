# authx/services/bootstrap.py

from __future__ import annotations

from django.db import transaction

from accounts.models import (
    Company,
    Dealership,
    DealershipMembership,
    DealershipRole,
    MembershipStatus,
)


@transaction.atomic
def bootstrap_account_for_user(*, user, company_name: str):
    company_name = company_name.strip() or user.email.split("@")[0]

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
    )

    return company, dealership, membership