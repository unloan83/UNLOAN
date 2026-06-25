from datetime import datetime, timezone
from math import pow
from typing import Any, Dict, List

from app.models.planner import (
    ActionItem,
    Allocation,
    CategoryAmount,
    CoachInsight,
    Debt,
    Goal,
    GoalPlan,
    IncomeProfile,
    PlannerRecord,
    PlanSummary,
    Profile,
    Projection,
    Recommendation,
    RoadmapPhase,
    MilestoneProjection,
)


class PlannerService:
    INFLATION = 0.06
    RETURNS = {"conservative": 0.07, "balanced": 0.10, "growth": 0.12}
    REGION_FACTORS = {"metro": 1.15, "urban": 1.05, "semi_urban": 0.95, "rural": 0.85, "global": 1.20}
    LIQUID_ASSET_KEYS = {"bank_savings", "emergency_fund", "fixed_deposit", "recurring_deposit"}
    VOLATILE_ASSET_KEYS = {"stocks", "mutual_funds", "crypto"}
    HIGH_COST_DEBT_KEYS = {"credit_card", "personal_loan", "friends_family", "other_loan"}

    @staticmethod
    def _number(payload: Dict[str, Any], key: str, default: float = 0) -> float:
        try:
            number = float(payload.get(key, default) or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key.replace('_', ' ').title()} must be a number.") from exc
        if number < 0:
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be negative.")
        return number

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(value, high))

    @staticmethod
    def _future_value(starting: float, monthly: float, years: int, annual_return: float, annual_growth: float) -> float:
        value = starting
        contribution = monthly
        monthly_rate = annual_return / 12
        for month in range(years * 12):
            value = value * (1 + monthly_rate) + contribution
            if month and month % 12 == 0:
                contribution *= 1 + annual_growth
        return value

    @staticmethod
    def _monthly_sip(target: float, years: float, annual_return: float) -> float:
        months = max(int(years * 12), 1)
        rate = annual_return / 12
        factor = (pow(1 + rate, months) - 1) / rate
        return target / factor if factor else target / months

    def _category_amounts(self, values: Any, label: str) -> List[CategoryAmount]:
        if not isinstance(values, list):
            raise ValueError(f"{label} must be a list.")
        rows = []
        for item in values:
            if not isinstance(item, dict):
                continue
            amount = self._number(item, "amount")
            if amount <= 0:
                continue
            rows.append(CategoryAmount(
                key=str(item.get("key", "custom")),
                name=str(item.get("name", label)).strip() or label,
                amount=amount,
            ))
        return rows

    def generate(self, payload: Dict[str, Any]) -> PlannerRecord:
        plan_mode = str(payload.get("planMode", "detailed"))
        if plan_mode not in {"short", "detailed"}:
            plan_mode = "detailed"
        profile_data = payload.get("profile", {})
        income_data = payload.get("income", {})
        if not isinstance(profile_data, dict) or not isinstance(income_data, dict):
            raise ValueError("Profile and income details are required.")

        age = int(self._number(profile_data, "age"))
        if not 18 <= age <= 80:
            raise ValueError("Age must be between 18 and 80.")
        region = str(profile_data.get("region", "urban"))
        if region not in self.REGION_FACTORS:
            raise ValueError("Choose a valid region.")
        risk_profile = str(profile_data.get("riskProfile", "balanced"))
        if risk_profile not in self.RETURNS:
            raise ValueError("Choose a valid investment style.")
        profile = Profile(
            name=str(profile_data.get("name", "")).strip() or "Friend",
            age=age,
            city=str(profile_data.get("city", "")).strip() or "Your city",
            region=region,
            employment_status=str(profile_data.get("employmentStatus", "salaried")),
            marital_status=str(profile_data.get("maritalStatus", "single")),
            dependents=int(self._number(profile_data, "dependents")),
            financial_goal_category=str(profile_data.get("financialGoalCategory", "wealth")),
            risk_profile=risk_profile,
        )

        monthly_income = self._number(income_data, "monthlyIncome")
        other_income = self._number(income_data, "otherIncome")
        if monthly_income + other_income <= 0:
            raise ValueError("Add at least one source of monthly income.")
        annual_growth = self._clamp(self._number(income_data, "annualGrowth", 5), 0, 30) / 100
        income = IncomeProfile(
            monthly_income=monthly_income,
            other_income=other_income,
            total_income=monthly_income + other_income,
            stability=str(income_data.get("stability", "stable")),
            annual_growth=round(annual_growth * 100, 1),
        )

        expenses = self._category_amounts(payload.get("expenses", []), "Expense")
        investments = self._category_amounts(payload.get("investments", []), "Investment")
        debts = self._debts(payload.get("debts", []))
        goals = self._goals(payload.get("goals", []))

        monthly_expenses = sum(item.amount for item in expenses)
        monthly_debt_emi = sum(item.emi for item in debts)
        liabilities = sum(item.outstanding for item in debts)
        assets = sum(item.amount for item in investments)
        total_outflow = monthly_expenses + monthly_debt_emi
        surplus = income.total_income - total_outflow
        if surplus <= 0:
            raise ValueError("Your selected expenses and EMIs are higher than income. Review them before building a wealth plan.")

        savings_ratio = surplus / income.total_income
        debt_ratio = monthly_debt_emi / income.total_income
        essential_keys = {"rent", "home_loan_emi", "food", "transport", "utilities", "insurance", "education", "healthcare", "parents_support", "child_expenses", "domestic_help"}
        essential_spend = sum(item.amount for item in expenses if item.key in essential_keys) + monthly_debt_emi
        if essential_spend == 0:
            essential_spend = monthly_expenses * 0.65 + monthly_debt_emi
        stability_months = {"variable": 9, "moderate": 7, "stable": 6}.get(income.stability, 6)
        emergency_target = essential_spend * stability_months * self.REGION_FACTORS[region]
        emergency_fund = sum(item.amount for item in investments if item.key in self.LIQUID_ASSET_KEYS)
        emergency_gap = max(emergency_target - emergency_fund, 0)
        emergency_progress = int(self._clamp(round((emergency_fund / emergency_target) * 100), 0, 100)) if emergency_target else 100

        high_cost_debt = sum(item.outstanding for item in debts if item.key in self.HIGH_COST_DEBT_KEYS or item.interest_rate >= 12)
        safety_alloc = min(surplus * (0.30 if emergency_gap else 0.05), emergency_gap / 18 if emergency_gap else surplus * 0.05)
        debt_alloc = min(surplus * (0.35 if high_cost_debt else 0.10), high_cost_debt / 24 if high_cost_debt else surplus * 0.10)
        investable = max(surplus - safety_alloc - debt_alloc, 0)
        goal_alloc = investable * (0.60 if goals else 0)
        wealth_alloc = investable - goal_alloc
        expected_return = self.RETURNS[risk_profile]
        goal_plans = self._goal_plans(goals, goal_alloc, expected_return)
        allocation = Allocation(
            safety=round(safety_alloc, 2),
            debt_freedom=round(debt_alloc, 2),
            goals=round(goal_alloc, 2),
            wealth=round(wealth_alloc, 2),
        )

        score = self._score(savings_ratio, debt_ratio, emergency_progress, investments, liabilities, assets)
        score_reasons = self._score_reasons(savings_ratio, debt_ratio, emergency_progress, investments, assets, liabilities)
        recommendations = self._recommendations(
            profile, income, savings_ratio, debt_ratio, emergency_gap, emergency_progress,
            high_cost_debt, expenses, investments, goal_plans,
        )
        projections = self._projections(assets, wealth_alloc + goal_alloc, expected_return, annual_growth)
        net_worth = assets - liabilities
        roadmap = self._roadmap(emergency_gap, high_cost_debt, goal_plans, wealth_alloc, profile)
        action_plan = self._action_plan(surplus, savings_ratio, safety_alloc, debt_alloc, goal_alloc + wealth_alloc, expenses)
        milestone_projections = self._milestones(
            net_worth, liabilities, emergency_fund, emergency_target, safety_alloc,
            debt_alloc + monthly_debt_emi, goal_alloc + wealth_alloc, expected_return,
            monthly_expenses, profile.age,
        )
        coach_insights = self._coach_insights(
            profile, income, savings_ratio, debt_ratio, emergency_progress,
            high_cost_debt, investments, expenses, goal_plans, action_plan,
        )
        summary = PlanSummary(
            monthly_income=round(income.total_income, 2),
            monthly_expenses=round(monthly_expenses, 2),
            monthly_debt_emi=round(monthly_debt_emi, 2),
            monthly_surplus=round(surplus, 2),
            savings_ratio=round(savings_ratio * 100, 1),
            debt_ratio=round(debt_ratio * 100, 1),
            assets=round(assets, 2), liabilities=round(liabilities, 2), net_worth=round(net_worth, 2),
            emergency_target=round(emergency_target, 2), emergency_fund=round(emergency_fund, 2),
            emergency_progress=emergency_progress,
            health_score=score, health_label=self._health_label(score), score_reasons=score_reasons,
            coach_message=self._coach_message(profile.name, score, savings_ratio, emergency_progress),
            wealth_stage=self._wealth_stage(net_worth, liabilities, emergency_progress),
            allocation=allocation, goals=goal_plans, projections=projections,
            recommendations=recommendations,
            expense_breakdown=sorted(expenses, key=lambda item: item.amount, reverse=True),
            asset_breakdown=sorted(investments, key=lambda item: item.amount, reverse=True),
            debt_breakdown=sorted(debts, key=lambda item: item.interest_rate, reverse=True),
            roadmap=roadmap, action_plan=action_plan,
            milestone_projections=milestone_projections, coach_insights=coach_insights,
            assumptions=[
                f"Expected scenario uses {expected_return * 100:.0f}% annual return; conservative scenario uses 6%.",
                f"Contributions rise {annual_growth * 100:.1f}% yearly with expected income growth.",
                "Goal costs use 6% inflation. Taxes, fees and product details are excluded.",
            ],
        )
        return PlannerRecord(
            plan_mode=plan_mode,
            profile=profile, income=income, expenses=expenses, investments=investments,
            debts=debts, selected_goals=goals, summary=summary,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _debts(self, values: Any) -> List[Debt]:
        if not isinstance(values, list):
            raise ValueError("Debts must be a list.")
        rows = []
        for item in values:
            if not isinstance(item, dict):
                continue
            outstanding = self._number(item, "outstanding")
            emi = self._number(item, "emi")
            if outstanding <= 0 and emi <= 0:
                continue
            rows.append(Debt(
                key=str(item.get("key", "other_loan")), name=str(item.get("name", "Loan")),
                outstanding=outstanding, emi=emi,
                interest_rate=self._clamp(self._number(item, "interestRate"), 0, 60),
                tenure_months=int(self._number(item, "tenureMonths")),
            ))
        return rows

    def _goals(self, values: Any) -> List[Goal]:
        if not isinstance(values, list):
            raise ValueError("Goals must be a list.")
        rows = []
        for item in values:
            if not isinstance(item, dict):
                continue
            amount = self._number(item, "targetAmount")
            years = self._number(item, "targetYears")
            if amount <= 0 or years <= 0:
                continue
            rows.append(Goal(
                key=str(item.get("key", "custom_goal")), name=str(item.get("name", "Goal")),
                target_amount=amount, target_years=years,
                priority=str(item.get("priority", "medium")),
            ))
        return rows

    def _goal_plans(self, goals: List[Goal], monthly_pool: float, annual_return: float) -> List[GoalPlan]:
        weights = {"high": 1.5, "medium": 1.0, "low": 0.65}
        calculations = []
        for goal in goals:
            future_cost = goal.target_amount * pow(1 + self.INFLATION, goal.target_years)
            goal_return = min(annual_return, 0.07) if goal.target_years <= 3 else annual_return
            required = self._monthly_sip(future_cost, goal.target_years, goal_return)
            calculations.append((goal, future_cost, required, required * weights.get(goal.priority, 1)))
        total_weight = sum(item[3] for item in calculations) or 1
        plans = []
        for goal, future_cost, required, weighted in calculations:
            allocated = monthly_pool * weighted / total_weight
            ratio = int(self._clamp(round(allocated / required * 100), 0, 100))
            if ratio >= 90:
                status, advice = "On track", "Automate this amount and increase it with income."
            elif ratio >= 55:
                status, advice = "Within reach", "A small monthly step-up or a longer timeline closes the gap."
            else:
                status, advice = "Needs a choice", "Lower the target, extend time, or focus on this before lower-priority goals."
            plans.append(GoalPlan(
                key=goal.key, name=goal.name, priority=goal.priority, target_years=goal.target_years,
                future_cost=round(future_cost, 2), monthly_required=round(required, 2),
                monthly_allocated=round(allocated, 2), funding_ratio=ratio, status=status, advice=advice,
            ))
        return sorted(plans, key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(item.priority, 1), item.target_years))

    def _score(self, savings_ratio: float, debt_ratio: float, emergency_progress: int, investments: List[CategoryAmount], liabilities: float, assets: float) -> int:
        cashflow = self._clamp(savings_ratio / 0.30 * 35, 0, 35)
        debt = self._clamp((1 - debt_ratio / 0.40) * 25, 0, 25)
        safety = emergency_progress / 100 * 25
        diversification = min(len({item.key for item in investments}), 4) / 4 * 10
        solvency = 5 if assets >= liabilities else self._clamp(assets / liabilities * 5, 0, 5) if liabilities else 5
        return int(round(self._clamp(cashflow + debt + safety + diversification + solvency, 0, 100)))

    @staticmethod
    def _health_label(score: int) -> str:
        if score >= 80: return "Strong"
        if score >= 65: return "Good"
        if score >= 45: return "Improving"
        return "Needs Attention"

    @staticmethod
    def _score_reasons(savings_ratio, debt_ratio, emergency_progress, investments, assets, liabilities):
        reasons = []
        reasons.append(f"Savings capacity is {'strong' if savings_ratio >= .25 else 'building' if savings_ratio >= .15 else 'a good next focus'} at {savings_ratio * 100:.1f}% of income.")
        reasons.append(f"EMIs use {debt_ratio * 100:.1f}% of income, which is {'comfortable' if debt_ratio <= .20 else 'manageable' if debt_ratio <= .30 else 'a pressure point'}.")
        reasons.append(f"Your liquid savings cover {emergency_progress}% of the suggested calm-money target.")
        if investments:
            reasons.append(f"Your assets span {len({item.key for item in investments})} selected savings or investment categories.")
        if liabilities > assets:
            reasons.append("Growing assets ahead of liabilities can lift your score over time.")
        return reasons[:4]

    @staticmethod
    def _wealth_stage(net_worth: float, liabilities: float, emergency_progress: int) -> str:
        if net_worth >= 10000000: return "Wealth builder"
        if net_worth >= 1000000 and emergency_progress >= 75: return "Momentum maker"
        if net_worth > 0: return "Foundation builder"
        if liabilities > 0: return "Debt reset"
        return "Fresh start"

    @staticmethod
    def _coach_message(name: str, score: int, savings_ratio: float, emergency_progress: int) -> str:
        if score >= 80:
            return f"{name}, your foundation is strong. Your next advantage is consistency—not complexity."
        if emergency_progress < 50:
            return f"{name}, you have room to grow. Start with one practical monthly transfer and build from there."
        if savings_ratio < 0.15:
            return f"{name}, the fastest win is creating breathing room in monthly cash flow before chasing returns."
        return f"{name}, you are building real momentum. A few focused moves can make your goals much more achievable."

    def _recommendations(self, profile, income, savings_ratio, debt_ratio, emergency_gap, emergency_progress, high_cost_debt, expenses, investments, goals):
        items = []
        has_insurance = any(item.key in {"insurance", "healthcare"} for item in expenses) or any(item.key == "insurance_savings" for item in investments)
        selected_emergency = any(goal.key == "emergency_goal" for goal in goals)
        if savings_ratio < 0.20:
            items.append(Recommendation("Savings habit", "Start with a practical payday transfer", "Move a fixed amount soon after income arrives, then increase it gradually every quarter.", "Builds consistency"))
        if not has_insurance:
            items.append(Recommendation("Protection", "Review health and life cover", "A simple insurance review can protect the roadmap you are building for yourself and your family.", "Protects progress"))
        if high_cost_debt:
            items.append(Recommendation("EMI planning", "Pay down the costliest loan first", "Keep regular EMIs going, then send extra money to the highest-interest balance.", "Saves interest"))
        if debt_ratio > 0.30:
            items.append(Recommendation("Cash flow", "Bring EMIs toward a comfortable range", "Pause new borrowing and use bonuses or windfalls to reduce principal faster.", "More monthly flexibility"))
        if goals:
            lead_goal = goals[0]
            items.append(Recommendation("Milestone", f"Make {lead_goal.name} the lead goal", "Fund the most important milestone first, then add lower-priority goals as income grows.", "Improves achievability"))
        lifestyle = sum(item.amount for item in expenses if item.key in {"lifestyle", "subscriptions", "miscellaneous"})
        if lifestyle > income.total_income * 0.15:
            items.append(Recommendation("Spending", "Create a guilt-free lifestyle cap", "Your flexible spending is above 15% of income. Trim it gently and automate the difference.", "Instant savings lift"))
        good_to_have = [goal for goal in goals if goal.key in {"travel", "marriage", "buy_vehicle"}]
        if good_to_have:
            items.append(Recommendation("Good-to-have", "Keep flexible goals in a separate bucket", "Travel, celebrations and upgrades work best after essentials and lead milestones are automated.", "Keeps joy planned"))
        if not any(item.key in self.VOLATILE_ASSET_KEYS for item in investments) and savings_ratio >= 0.15:
            items.append(Recommendation("Investing", "Begin diversified long-term investing", "Consider broad diversified funds aligned with your comfort level and timeline.", "Supports compounding"))
        if goals and any(goal.funding_ratio < 55 for goal in goals):
            items.append(Recommendation("Goals", "Choose a lead milestone", "Fully fund one high-priority goal before splitting contributions across every ambition.", "Improves achievability"))
        if emergency_gap and (selected_emergency or len(items) < 4):
            items.append(Recommendation("Calm money", "Build a simple backup reserve gradually", f"Your liquid savings are {emergency_progress}% of the suggested guide. Add to it after essentials and selected goals are moving.", "Adds flexibility"))
        if income.annual_growth < 5:
            items.append(Recommendation("Income", "Invest in earning power", "A course, credential, negotiation plan, or side income can improve every goal at once.", "Raises future capacity"))
        if not items:
            items.append(Recommendation("Momentum", "Automate and review", "Keep investments automated and revisit this plan every six months or after a major life change.", "Protects consistency"))
        return items[:5]

    @staticmethod
    def _roadmap(emergency_gap, high_cost_debt, goals, wealth_alloc, profile):
        priority_goal = goals[0].name if goals else "your first wealth milestone"
        return [
            RoadmapPhase("Month 1–3", "Cash-flow clarity", "Track real spending, automate bills and start one payday transfer.", f"Create a steady rhythm from {profile.employment_status.replace('_', ' ')} income."),
            RoadmapPhase("Month 4–6", "Necessities first", "Review essentials, insurance and EMI comfort before adding extra goals.", "Make your monthly plan easy to repeat."),
            RoadmapPhase("Month 7–12", "Goal momentum", "Pay costly debt faster while starting or increasing automatic investments.", f"Move {priority_goal} from idea to monthly action." if not high_cost_debt else f"Free cash flow by reducing {money_text(high_cost_debt)} of costlier debt."),
            RoadmapPhase("Year 2–3", "Wealth acceleration", "Increase contributions with every income rise and review goal funding annually.", f"Push {priority_goal} toward full monthly funding."),
            RoadmapPhase("Year 5+", "Long-term wealth creation", "Keep a diversified allocation aligned to capacity, age and goal timelines.", f"Grow the current long-term allocation of {money_text(wealth_alloc)} per month."),
        ]

    @staticmethod
    def _action_plan(surplus, savings_ratio, safety_alloc, debt_alloc, investment_alloc, expenses):
        discretionary = sum(item.amount for item in expenses if item.key in {"lifestyle", "subscriptions", "miscellaneous"})
        healthy_saving = max(surplus, 0) if savings_ratio >= .20 else max(surplus + discretionary * .15, 0)
        reduction = round(discretionary * .15, 2) if savings_ratio < .20 and discretionary else 0
        actions = []
        if reduction:
            actions.append(ActionItem("Reduce flexible spending", round(reduction, 2), "Redirect roughly 15% of discretionary spending without cutting essentials."))
        if debt_alloc:
            actions.append(ActionItem("Make an extra debt payment", round(debt_alloc, 2), "Apply this above minimum EMIs to the highest-interest balance first."))
        if investment_alloc:
            actions.append(ActionItem("Automate goal and wealth investing", round(investment_alloc, 2), "Transfer it soon after payday and step it up with income."))
        if safety_alloc:
            actions.append(ActionItem("Build calm-money savings", round(safety_alloc, 2), "Keep this liquid and grow it gradually alongside your main roadmap."))
        if not actions:
            actions.append(ActionItem("Protect your monthly savings habit", round(healthy_saving, 2), "Automation is the simplest way to preserve momentum."))
        return actions[:5]

    def _months_to_value(self, starting, monthly, target, annual_return, max_months=600):
        if starting >= target:
            return 0
        if monthly <= 0:
            return None
        value = starting
        rate = annual_return / 12
        for month in range(1, max_months + 1):
            value = value * (1 + rate) + monthly
            if value >= target:
                return month
        return None

    @staticmethod
    def _date_after_months(months):
        if months is None:
            return "Beyond current plan"
        date = datetime.now(timezone.utc)
        year = date.year + (date.month - 1 + months) // 12
        month = (date.month - 1 + months) % 12 + 1
        return datetime(year, month, 1, tzinfo=timezone.utc).strftime("%b %Y")

    def _milestones(self, net_worth, liabilities, emergency_fund, emergency_target, safety_alloc, debt_payment, monthly_investment, annual_return, monthly_expenses, age):
        emergency_gap = max(emergency_target - emergency_fund, 0)
        emergency_months = 0 if not emergency_gap else int(round(emergency_gap / safety_alloc)) if safety_alloc else None
        debt_months = 0 if not liabilities else int(round(liabilities / debt_payment)) if debt_payment else None
        liquid_base = max(net_worth, 0)
        targets = [("First ₹1 lakh savings", 100000), ("First ₹5 lakh net worth", 500000), ("First ₹10 lakh net worth", 1000000)]
        rows = [MilestoneProjection(
            "Calm-money reserve", self._date_after_months(emergency_months),
            int(self._clamp(round(emergency_fund / emergency_target * 100), 0, 100)) if emergency_target else 100,
            f"Suggested guide: {money_text(emergency_target)} in liquid reserves.",
        )]
        for name, target in targets:
            months = self._months_to_value(liquid_base, monthly_investment, target, annual_return)
            rows.append(MilestoneProjection(name, self._date_after_months(months), int(self._clamp(round(liquid_base / target * 100), 0, 100)), f"Assumes {money_text(monthly_investment)} monthly and no withdrawals."))
        rows.append(MilestoneProjection("Debt-free date", self._date_after_months(debt_months), 100 if liabilities == 0 else 0, "Estimate assumes current EMI plus the recommended extra payment."))
        retirement_target = monthly_expenses * 12 * 25
        retirement_progress = int(self._clamp(round(max(net_worth, 0) / retirement_target * 100), 0, 100)) if retirement_target else 0
        rows.append(MilestoneProjection("Retirement readiness", f"Age {max(age + 1, 60)} planning view", retirement_progress, f"Illustrative corpus target: {money_text(retirement_target)} (25× annual expenses)."))
        return rows

    @staticmethod
    def _coach_insights(profile, income, savings_ratio, debt_ratio, emergency_progress, high_cost_debt, investments, expenses, goals, actions):
        doing_well = "You have positive monthly breathing room to direct intentionally." if savings_ratio >= .15 else "You completed the hardest first step: seeing the full picture clearly."
        opportunity = "Paying down costlier debt can free up more future investing capacity." if high_cost_debt else "Your next layer is a steady reserve plus regular goal investing." if emergency_progress < 75 else "Consistency is your biggest advantage from here."
        fix_first = "Automate the first affordable monthly transfer and build from there." if emergency_progress < 75 else "Clear the highest-interest balance before adding lower-priority goals." if high_cost_debt else "Automate the recommended monthly split."
        next_action = actions[0].action + f" by {money_text(actions[0].monthly_amount)} this month." if actions else "Set one automatic payday transfer."
        habit = "Increase automatic savings by half of every future pay raise." if income.annual_growth else "Review cash flow for ten minutes on the same date each month."
        if profile.age <= 35 and income.stability == "stable" and debt_ratio < .20 and emergency_progress >= 75:
            habit = "Use your long time horizon: automate diversified long-term investing and avoid reacting to short-term market noise."
        if profile.age >= 50 and not any(item.key == "retirement_funds" for item in investments):
            fix_first = "Make retirement accumulation a top-priority goal and review the required corpus with a certified adviser."
        if profile.dependents:
            opportunity += " With dependents, a health and term-cover review can strengthen the plan."
        return [
            CoachInsight("What’s working", "You already have something to build on", doing_well),
            CoachInsight("Next opportunity", "You can improve this gradually", opportunity),
            CoachInsight("Practical step", "Your next practical step", fix_first),
            CoachInsight("Next 30 days", "One concrete move", next_action),
            CoachInsight("Best habit", "The move with lasting impact", habit),
        ]

    def _projections(self, starting: float, monthly: float, expected_return: float, annual_growth: float) -> List[Projection]:
        rows = []
        for years in (5, 10, 20):
            contributed = starting + sum(monthly * 12 * pow(1 + annual_growth, year) for year in range(years))
            rows.append(Projection(
                years=years, contributed=round(contributed, 2),
                conservative=round(self._future_value(starting, monthly, years, 0.06, annual_growth), 2),
                expected=round(self._future_value(starting, monthly, years, expected_return, annual_growth), 2),
            ))
        return rows


def money_text(value: float) -> str:
    value = max(float(value or 0), 0)
    if value >= 10000000:
        return f"₹{value / 10000000:.2f} crore"
    if value >= 100000:
        return f"₹{value / 100000:.1f} lakh"
    return f"₹{value:,.0f}"
