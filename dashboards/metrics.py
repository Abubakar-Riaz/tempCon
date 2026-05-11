from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

from django.core.cache import cache
from django.db import models
from django.db.models import (
    Avg, Case, Count, DecimalField, F, OuterRef, Q, Subquery, Sum, Value, When
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import status

from backend.permissions import (
    IsUserActive, HasCompanyContext, IsCompanyMember, HasActiveSubscription,
)
from backend.response import ok, fail  # ← sugar helpers

from accounts.models import Company, Dealership  # PublicIDMixin with public_id  :contentReference[oaicite:7]{index=7}
from billing.models import Subscription  # is_active property                    :contentReference[oaicite:8]{index=8}

from buying.models import BuyingDecision, Decision                          # WIN/LOSS/PENDING  :contentReference[oaicite:9]{index=9}
from hammer.models import HammerSession, SessionStatus                      # est_cost_total    :contentReference[oaicite:10]{index=10}
from inspections.models import Inspection, InspectionStatus, Trade          # statuses/trades   :contentReference[oaicite:11]{index=11}
from inventory.models import Vehicle                                        # vehicle scope     :contentReference[oaicite:12]{index=12}
from recon.models import WorkItem                                           # recon costs       :contentReference[oaicite:13]{index=13}

# Optional fast-path (pre-aggregated shards)
from dashboards.models import KPIShard, KPIScope

CACHE_TTL = 90  # seconds


@dataclass
class DashboardPayload:
    vehicles: Dict[str, Any]
    inspections: Dict[str, Any]
    financial: Dict[str, Any]
    trades: list
    recentActivity: list

    def as_dict(self) -> Dict[str, Any]:
        return {
            "vehicles": self.vehicles,
            "inspections": self.inspections,
            "financial": self.financial,
            "trades": self.trades,
            "recentActivity": self.recentActivity,
        }


class DashboardsCompanyMetricsView(APIView):
    """
    GET /api/v1/dashboards/companies/{company_id}/metrics
    Query:
      - scope: COMPANY (default) | DEALERSHIP
      - dealership_id: public UUID (required when scope=DEALERSHIP)
    """
    permission_classes = [IsUserActive, HasCompanyContext, IsCompanyMember, HasActiveSubscription]

    def get(self, request: Request, company_id):
        try:
            scope = (request.query_params.get("scope") or "COMPANY").upper()
            dlr_pub_id = request.query_params.get("dealership_id")

            # Resolve company
            company: Optional[Company] = Company.objects.filter(public_id=company_id).first()
            if not company:
                return fail("NOT_FOUND", "Company not found.", status=404, request=request)

            dealership: Optional[Dealership] = None
            if scope == "DEALERSHIP":
                if not dlr_pub_id:
                    return fail("BAD_REQUEST", "dealership_id is required for DEALERSHIP scope.", status=400, request=request)
                dealership = Dealership.objects.filter(company=company, public_id=dlr_pub_id).first()  # public_id lookup  :contentReference[oaicite:15]{index=15}
                if not dealership:
                    return fail("NOT_FOUND", "Dealership not found.", status=404, request=request)

            cache_key = f"dashboard:{company.public_id}:{scope}:{getattr(dealership, 'public_id', '-')}"
            cached = cache.get(cache_key)
            if cached:
                return ok(cached, request=request)

            # ---- Optional fast-path via KPIShard (latest for today) -----------------
            today = date.today()
            shard_scope = KPIScope.DEALERSHIP if dealership else KPIScope.COMPANY
            shard = KPIShard.objects.filter(
                scope=shard_scope,
                company=company,
                dealership=dealership,
                key="dashboard.v1.snapshot",
                as_of_date=today,
            ).order_by("-computed_at").first()
            if shard and isinstance(shard.value, dict):
                # trust shape, but ensure all keys present
                val = shard.value
                payload = {
                    "vehicles": val.get("vehicles") or {"total": 0, "pending": 0, "completed": 0, "won": 0, "lost": 0},
                    "inspections": val.get("inspections") or {"inProgress": 0, "avgDuration": 0.0},
                    "financial": val.get("financial") or {"totalValue": 0, "avgHammerCost": 0, "wonValue": 0, "lostValue": 0},
                    "trades": val.get("trades") or [],
                    "recentActivity": val.get("recentActivity") or [],
                }
                cache.set(cache_key, payload, CACHE_TTL)
                return ok(payload, request=request)

            # ----------------- Live compute -----------------
            vehicle_filter = Q(company=company)
            if dealership:
                vehicle_filter &= Q(dealership=dealership)

            vehicles_qs = Vehicle.objects.filter(vehicle_filter).only("id")  # lean base

            # Latest inspection status per vehicle
            latest_insp_sub = (Inspection.objects
                               .filter(vehicle=OuterRef("pk"))
                               .order_by("-id")
                               .values("status")[:1])  # status enum (DRAFT/IN_PROGRESS/COMPLETED)  :contentReference[oaicite:16]{index=16}

            vehicles_annotated = vehicles_qs.annotate(latest_insp_status=Subquery(latest_insp_sub))

            # Buying decision per vehicle (one-to-one)
            decision_sub = (BuyingDecision.objects
                            .filter(vehicle=OuterRef("pk"))
                            .values("decision")[:1])  # WIN/LOSS/PENDING  :contentReference[oaicite:17]{index=17}
            vehicles_annotated = vehicles_annotated.annotate(decision=Subquery(decision_sub))

            # Totals
            total_vehicles = vehicles_qs.count()
            completed = vehicles_annotated.filter(latest_insp_status=InspectionStatus.COMPLETED).count()
            pending = vehicles_annotated.filter(
                Q(latest_insp_status__isnull=True) |
                Q(latest_insp_status__in=[InspectionStatus.DRAFT, InspectionStatus.IN_PROGRESS])
            ).count()
            won = vehicles_annotated.filter(decision=Decision.WIN).count()
            lost = vehicles_annotated.filter(decision=Decision.LOSS).count()

            vehicles_block = {
                "total": total_vehicles,
                "pending": pending,
                "completed": completed,
                "won": won,
                "lost": lost,
            }

            # Inspections block
            insp_filter = Q(vehicle__in=vehicles_qs)
            in_progress = Inspection.objects.filter(insp_filter, status=InspectionStatus.IN_PROGRESS).count()  # :contentReference[oaicite:18]{index=18}

            # avg duration in hours for completed
            completed_qs = Inspection.objects.filter(insp_filter, status=InspectionStatus.COMPLETED)  # :contentReference[oaicite:19]{index=19}
            # duration seconds: COALESCE(completed_at - started_at, completed_at - created_at)
            duration_expr = (models.ExpressionWrapper(
                Coalesce(F("completed_at") - F("started_at"), F("completed_at") - F("created_at")),
                output_field=models.DurationField(),
            ))
            agg = completed_qs.aggregate(avg_duration=Avg(duration_expr))
            avg_hours = 0.0
            if agg["avg_duration"]:
                avg_hours = round(agg["avg_duration"].total_seconds() / 3600.0, 2)

            inspections_block = {
                "inProgress": in_progress,
                "avgDuration": avg_hours,
            }

            # Financials
            # Avg hammer cost: use HammerSession.est_cost_total (FINALIZED preferred, else any)
            hs_filter = Q(vehicle__in=vehicles_qs)
            hs_qs = HammerSession.objects.filter(hs_filter)
            # Prefer FINALIZED; if none finalized exist, use all
            if hs_qs.filter(status=SessionStatus.FINALIZED).exists():  # :contentReference[oaicite:20]{index=20}
                hs_qs = hs_qs.filter(status=SessionStatus.FINALIZED)

            hammer_avg = hs_qs.aggregate(v=Avg("est_cost_total"))["v"] or 0
            hammer_sum = hs_qs.aggregate(s=Sum("est_cost_total"))["s"] or 0

            # Fallback totals via recon work items for vehicles without hammer session
            wi_filter = Q(recon_case__vehicle__in=vehicles_qs)
            wi_qs = WorkItem.objects.filter(wi_filter)
            recon_sum = wi_qs.aggregate(
                s=Sum(models.Case(
                    When(actual_cost__isnull=False, then=F("actual_cost")),
                    default=F("est_cost"),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ))
            )["s"] or 0

            # totalValue heuristic: prioritize hammer_sum if present; else recon_sum
            total_value = hammer_sum if hammer_sum else recon_sum

            # won/lost value: join vehicle → decision; value comes from hammer if exists else recon fallback
            # For simplicity, reuse the same heuristic per subset.
            # (If you keep a dedicated vehicle valuation field, swap here.)
            dec_base = vehicles_annotated.values("id", "decision")
            # vehicles that have a hammer session
            hs_map = dict(hs_qs.values_list("vehicle_id", "est_cost_total"))
            # recon per-vehicle fallback
            wi_per_vehicle = (wi_qs
                              .values(v_id=F("recon_case__vehicle_id"))
                              .annotate(
                                  v=Sum(models.Case(
                                      When(actual_cost__isnull=False, then=F("actual_cost")),
                                      default=F("est_cost"),
                                      output_field=DecimalField(max_digits=12, decimal_places=2)
                                  ))
                              ))
            wi_map = {row["v_id"]: row["v"] for row in wi_per_vehicle}

            won_value = 0
            lost_value = 0
            for row in dec_base:
                vid = row["id"]
                v = hs_map.get(vid, wi_map.get(vid, 0)) or 0
                if row["decision"] == Decision.WIN:
                    won_value += v
                elif row["decision"] == Decision.LOSS:
                    lost_value += v

            financial_block = {
                "totalValue": float(total_value),
                "avgHammerCost": float(hammer_avg),
                "wonValue": float(won_value),
                "lostValue": float(lost_value),
            }

            # Trades (Top Trades): by WorkItem.trade label
            trades_rows = (
                wi_qs
                .values(name=F("trade__label"))   # human label snapshot      :contentReference[oaicite:21]{index=21}
                .annotate(
                    count=models.Count("recon_case__vehicle", distinct=True),
                    avgCost=Avg(models.Case(
                        When(actual_cost__isnull=False, then=F("actual_cost")),
                        default=F("est_cost"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )),
                )
                .order_by("-count", "name")[:10]
            )
            trades_block = [
                {"name": r["name"] or "Unassigned", "count": r["count"], "avgCost": float(r["avgCost"] or 0)}
                for r in trades_rows
            ]

            payload = DashboardPayload(
                vehicles=vehicles_block,
                inspections=inspections_block,
                financial=financial_block,
                trades=trades_block,
                recentActivity=[],  # reserved for future
            ).as_dict()

            cache.set(cache_key, payload, CACHE_TTL)
            return ok(payload, request=request)

        except Exception as e:
            print(e)
            return fail(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                request=request,
            )
