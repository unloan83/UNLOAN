from datetime import datetime, timezone
from typing import List, Dict, Any

from app.models.planner import (
    UserProfile,
    FinancialInput,
    Milestone,
    PlanAllocation,
    PlanSummary,
    PlannerRecord,
)


class PlannerService:
    @staticmethod
    def _normalize(mode: str, value: float) -> float:
        return value / 12 if mode == "yearly" else value

    @staticmethod
    def _clamp(val: float, low: float, high: float) -> float:
        return max(low, min(val, high))

    def generate(self, payload: Dict[str, Any]) -> PlannerRecord:
        profile = UserProfile(
            name=payload["name"].strip(),
            age=int(payload["age"]),
            mobile=payload["mobile"].strip(),
            dependents=int(payload.get("dependents", 0)),
            marital_status=payload.get("maritalStatus", "single"),
            has_health_insurance=bool(payload.get("hasHealthInsurance", False)),
            has_term_insurance=bool(payload.get("hasTermInsurance", False)),
        )

        mode = payload.get("inputMode", "monthly")
        financial = FinancialInput(
            mode=mode,
            income=self._normalize(mode, float(payload.get("income", 0))),
            rent=self._normalize(mode, float(payload.get("rent", 0))),
            food=self._normalize(mode, float(payload.get("food", 0))),
            misc=self._normalize(mode, float(payload.get("misc", 0))),
        )

        milestones = [
            Milestone(
                key=m["key"],
                name=m["name"],
                amount=float(m["amount"]),
                years=float(m["years"]),
            )
            for m in payload.get("milestones", [])
        ]

        total_expenses = financial.rent + financial.food + financial.misc
        surplus = financial.income - total_expenses
        if surplus <= 0:
            raise ValueError("Expenses exceed income. Please update values.")

        short_goals = [m for m in milestones if m.years <= 5]
        long_goals = [m for m in milestones if m.years > 5]

        insurance_alloc = max(surplus * 0.25, 3000 + profile.dependents * 700)
        remaining = max(surplus - insurance_alloc, 0)

        short_weight = sum(g.amount for g in short_goals)
        long_weight = sum(g.amount for g in long_goals)
        total_weight = short_weight + long_weight or 1

        short_alloc = remaining * (short_weight / total_weight)
        long_alloc = remaining * (long_weight / total_weight)

        insurance_target = financial.income * 12 * 12
        health_score, health_note = self._health_score(
            income=financial.income,
            expenses=total_expenses,
            surplus=surplus,
            insurance_alloc=insurance_alloc,
            insurance_target=insurance_target,
            has_health=profile.has_health_insurance,
            has_term=profile.has_term_insurance,
        )

        summary = PlanSummary(
            surplus=round(surplus, 2),
            health_score=health_score,
            health_note=health_note,
            insurance_target=round(insurance_target, 2),
            allocation=PlanAllocation(
                insurance=round(insurance_alloc, 2),
                short_term=round(short_alloc, 2),
                long_term=round(long_alloc, 2),
            ),
            notes=[
                f"Savings ratio: {(surplus / financial.income) * 100:.1f}%",
                "Inflation assumption used: 6% p.a.",
                "Term insurance thumb rule: 10x to 15x annual income.",
            ],
        )

        return PlannerRecord(
            profile=profile,
            financial=financial,
            milestones=milestones,
            summary=summary,
            consult=bool(payload.get("consult", False)),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _health_score(
        self,
        *,
        income: float,
        expenses: float,
        surplus: float,
        insurance_alloc: float,
        insurance_target: float,
        has_health: bool,
        has_term: bool,
    ) -> tuple[int, str]:
        savings_ratio = surplus / income if income > 0 else 0
        protection_ratio = (insurance_alloc * 12) / insurance_target if insurance_target > 0 else 0
        runway_months = (surplus / expenses) * 6 if expenses > 0 else 0

        savings_score = self._clamp(round((savings_ratio / 0.30) * 40), 0, 40)
        protection_score = self._clamp(round((protection_ratio / 0.08) * 30), 0, 30)
        stability_score = self._clamp(round((runway_months / 6) * 30), 0, 30)
        insurance_bonus = (6 if has_health else 0) + (6 if has_term else 0)
        total = int(self._clamp(savings_score + protection_score + stability_score + insurance_bonus, 0, 100))

        if total >= 80:
            note = "Excellent financial momentum."
        elif total >= 60:
            note = "Good base; improve protection and investment discipline."
        elif total >= 40:
            note = "Moderate health; increase surplus and emergency readiness."
        else:
            note = "At-risk profile; prioritize insurance and expense optimization."

        return total, note
