from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import DealershipMembership, MembershipStatus


class MyCompaniesView(APIView):
    """
    List every active company the authenticated user belongs to.
    Membership is derived from request.user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        memberships = (
            DealershipMembership.objects
            .filter(
                user=request.user,
                status=MembershipStatus.ACTIVE,
                company__is_active=True,
                dealership__is_active=True,
            )
            .select_related("company")
            .only(
                "is_company_owner",
                "company__id",
                "company__public_id",
                "company__name",
                "company__slug",
            )
            .order_by("company__name")
        )

        companies_by_id = {}

        for membership in memberships:
            company = membership.company

            if company.id not in companies_by_id:
                companies_by_id[company.id] = {
                    "id": str(company.public_id),
                    "name": company.name,
                    "slug": company.slug,
                    "is_company_owner": False,
                }

            companies_by_id[company.id]["is_company_owner"] = (
                companies_by_id[company.id]["is_company_owner"]
                or bool(membership.is_company_owner)
            )

        items = list(companies_by_id.values())

        return Response(
            {
                "count": len(items),
                "items": items,
            },
            status=status.HTTP_200_OK,
        )