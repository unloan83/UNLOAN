from datetime import datetime, timezone
from math import pow
from typing import Any, Dict, List

from app.models.planner import (
    FinancialInput,
    GoalRecommendation,
    Milestone,
    PlanAllocation,
    PlannerRecord,
    PlanSummary,
    Projection,
    UserProfile,
)


class PlannerService:
    INFLATION_RATE = 0.06
    RETURN_RATES = {"conservative": 0.07, "balanced": 0.10, "growth": 0.12}
    LOCATION_FACTORS = {
        "metro": 1.15,
        "tier1": 1.05,
        "tier2": 0.95,
        "tier3": 0.85,
        "outside_india": 1.20,
    }

    @staticmethod
    def _number(payload: Dict[str, Any], key: str, default: float = 0) -> float:
        try:
            value = float(payload.get(key, default))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key.replace('_', ' ').title()} must be a number.") from exc
        if value < 0:
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be negative.")
        return value

    @staticmethod
    def _normalize(mode: str, value: float) -> float:
        return value / 12 if mode == "yearly" else value

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(value, high))

    @staticmethod
    def _monthly_sip(target: float, years: float, annual_return: float) -> float:
        months = max(int(years * 12), 1)
        monthly_rate = annual_return / 12
        factor = (pow(1 + monthly_rate, months) - 1) / monthly_rate
        return target / factor if factor else target / months

    @staticmethod
    def _future_value(starting: float, monthly: float, years: int, annual_return: float) -> float:
        months = years * 12
        rate = annual_return / 12
        growth = pow(1 + rate, months)
        return starting * growth + monthly * ((growth - 1) / rate)

    def generate(self, payload: Dict[str, Any]) -> PlannerRecord:
        name = str(payload.get("name", "")).strip() or "Your"
        age = int(self._number(payload, "age"))
        retirement_age = int(self._number(payload, "retirementAge", 60))
        if not 18 <= age <= 80:
            raise ValueError("Age must be between 18 and 80.")
        if retirement_age <= age or retirement_age > 85:
            raise ValueError("Retirement age must be after your current age and no more than 85.")

        location = str(payload.get("location", "tier2"))
        risk_profile = str(payload.get("riskProfile", "balanced"))
        if location not in self.LOCATION_FACTORS:
            raise ValueError("Choose a valid location type.")
        if risk_profile not in self.RETURN_RATES:
            raise ValueError("Choose a valid risk profile.")

        profile = UserProfile(
            name=name,
            age=age,
            location=location,
            dependents=int(self._number(payload, "dependents")),
            marital_status=str(payload.get("maritalStatus", "single")),
            has_health_insurance=bool(payload.get("hasHealthInsurance", False)),
            has_term_insurance=bool(payload.get("hasTermInsurance", False)),
            risk_profile=risk_profile,
            retirement_age=retirement_age,
        )

        mode = str(payload.get("inputMode", "monthly"))
        if mode not in {"monthly", "yearly"}:
            raise ValueError("Input mode must be monthly or yearly.")
        monthly_keys = ("income", "rent", "food", "misc", "debtEmi")
        values = {key: self._normalize(mode, self._number(payload, key)) for key in monthly_keys}
        financial = FinancialInput(
            mode=mode,
            income=values["income"],
            rent=values["rent"],
            food=values["food"],
            misc=values["misc"],
            debt_emi=values["debtEmi"],
            current_savings=self._number(payload, "currentSavings"),
            current_investments=self._number(payload, "currentInvestments"),
        )
        if financial.income <= 0:
            raise ValueError("Income must be greater than zero.")

        milestones: List[Milestone] = []
        for item in payload.get("milestones", []):
            amount = self._number(item, "amount")
            years = self._number(item, "years")
            if amount <= 0 or years <= 0:
                raise ValueError("Each milestone needs a positive amount and timeline.")
            milestones.append(Milestone(
                key=str(item.get("key", "goal")),
                name=str(item.get("name", "Goal")).strip() or "Goal",
                amount=amount,
                years=years,
            ))

        expenses = financial.rent + financial.food + financial.misc + financial.debt_emi
        surplus = financial.income - expenses
        if surplus <= 0:
            raise ValueError("Monthly expenses and EMIs exceed income. Reduce spending before investing.")

        savings_ratio = surplus / financial.income
        debt_ratio = financial.debt_emi / financial.income
        essentials = financial.rent + financial.food + financial.debt_emi
        emergency_months = 9 if profile.dependents else 6
        emergency_target = essentials * emergency_months * self.LOCATION_FACTORS[location]
        emergency_gap = max(emergency_target - financial.current_savings, 0)

        emergency_alloc = min(
            surplus * (0.30 if emergency_gap else 0.05),
            emergency_gap / 12 if emergency_gap else surplus * 0.05,
        )
        protection_alloc = 0.0
        if not profile.has_health_insurance:
            protection_alloc += min(surplus * 0.08, 2500 + profile.dependents * 500)
        if profile.dependents and not profile.has_term_insurance:
            protection_alloc += min(surplus * 0.05, 1500)
        investable = max(surplus - emergency_alloc - protection_alloc, 0)
        goal_pool = investable * (0.65 if milestones else 0)
        retirement_alloc = investable - goal_pool

        years_to_retirement = retirement_age - age
        annual_return = self.RETURN_RATES[risk_profile]
        if years_to_retirement <= 7:
            annual_return = min(annual_return, 0.08)
        elif years_to_retirement <= 12:
            annual_return = min(annual_return, 0.10)
        goal_rows = self._goal_recommendations(milestones, goal_pool, annual_return)
        score = self._health_score(
            savings_ratio=savings_ratio,
            debt_ratio=debt_ratio,
            emergency_coverage=(financial.current_savings / emergency_target if emergency_target else 1),
            has_health=profile.has_health_insurance,
            has_term=profile.has_term_insurance or profile.dependents == 0,
        )
        projection_horizons = sorted({5, 10, 20, years_to_retirement})
        projections = [
            Projection(
                years=years,
                invested=round(financial.current_investments + investable * 12 * years, 2),
                projected_value=round(
                    self._future_value(financial.current_investments, investable, years, annual_return), 2
                ),
            )
            for years in projection_horizons
        ]
        allocation = PlanAllocation(
            emergency=round(emergency_alloc, 2),
            protection=round(protection_alloc, 2),
            milestones=round(goal_pool, 2),
            retirement=round(retirement_alloc, 2),
        )
        summary = PlanSummary(
            surplus=round(surplus, 2),
            savings_ratio=round(savings_ratio * 100, 1),
            debt_ratio=round(debt_ratio * 100, 1),
            health_score=score,
            health_note=self._health_note(score),
            emergency_target=round(emergency_target, 2),
            emergency_gap=round(emergency_gap, 2),
            insurance_target=round(financial.income * 12 * (12 if profile.dependents else 8), 2),
            allocation=allocation,
            goals=goal_rows,
            projections=projections,
            next_steps=self._next_steps(profile, emergency_gap, emergency_alloc, debt_ratio, goal_rows),
            assumptions=[
                f"Illustrative return: {annual_return * 100:.0f}% p.a. for a {risk_profile} portfolio; actual returns vary.",
                "Goal costs are increased by 6% annual inflation.",
                "Taxes, fees, existing cover and employer benefits are not included.",
            ],
        )
        return PlannerRecord(
            profile=profile,
            financial=financial,
            milestones=milestones,
            summary=summary,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _goal_recommendations(
        self, milestones: List[Milestone], monthly_pool: float, annual_return: float
    ) -> List[GoalRecommendation]:
        rows = []
        required = []
        for goal in milestones:
            future_cost = goal.amount * pow(1 + self.INFLATION_RATE, goal.years)
            rate = min(annual_return, 0.07) if goal.years <= 3 else annual_return
            required.append((goal, future_cost, self._monthly_sip(future_cost, goal.years, rate)))
        total_required = sum(item[2] for item in required) or 1
        for goal, future_cost, monthly_required in required:
            allocated = monthly_pool * (monthly_required / total_required)
            ratio = int(self._clamp(round(allocated / monthly_required * 100), 0, 100))
            if ratio >= 90:
                status, advice = "On track", "Automate this contribution and review it annually."
            elif ratio >= 50:
                status, advice = "Needs a boost", "Increase the monthly amount or extend the target date."
            else:
                status, advice = "Funding gap", "Prioritize this goal, reduce its cost, or move the timeline."
            rows.append(GoalRecommendation(
                key=goal.key,
                name=goal.name,
                years=goal.years,
                future_cost=round(future_cost, 2),
                monthly_required=round(monthly_required, 2),
                monthly_allocated=round(allocated, 2),
                funding_ratio=ratio,
                status=status,
                recommendation=advice,
            ))
        return rows

    def _health_score(
        self, *, savings_ratio: float, debt_ratio: float, emergency_coverage: float, has_health: bool, has_term: bool
    ) -> int:
        savings = self._clamp((savings_ratio / 0.30) * 35, 0, 35)
        debt = self._clamp((1 - debt_ratio / 0.40) * 20, 0, 20)
        emergency = self._clamp(emergency_coverage * 25, 0, 25)
        protection = (10 if has_health else 0) + (10 if has_term else 0)
        return int(round(self._clamp(savings + debt + emergency + protection, 0, 100)))

    @staticmethod
    def _health_note(score: int) -> str:
        if score >= 80:
            return "Strong foundation. Keep contributions automated and goals reviewed."
        if score >= 60:
            return "A healthy base with a few clear gaps to close."
        if score >= 40:
            return "Your plan can improve quickly by strengthening cash reserves and protection."
        return "Stabilize cash flow and debt first; investing comes after the foundation."

    @staticmethod
    def _next_steps(
        profile: UserProfile,
        emergency_gap: float,
        emergency_alloc: float,
        debt_ratio: float,
        goals: List[GoalRecommendation],
    ) -> List[str]:
        steps = []
        if emergency_gap:
            months = max(round(emergency_gap / emergency_alloc), 1) if emergency_alloc else 0
            steps.append(f"Build the emergency fund gap over about {months} months.")
        if not profile.has_health_insurance:
            steps.append("Compare personal health cover before increasing market investments.")
        if profile.dependents and not profile.has_term_insurance:
            steps.append("Add pure term cover; avoid mixing life insurance and investing.")
        if debt_ratio > 0.30:
            steps.append("Keep total EMIs below 30% of take-home income where possible.")
        if any(goal.status == "Funding gap" for goal in goals):
            steps.append("Fund one priority milestone fully before spreading money across every goal.")
        if not steps:
            steps.append("Automate monthly investments and review the plan every 6–12 months.")
        return steps[:4]
