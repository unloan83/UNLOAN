from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class Profile:
    name: str
    age: int
    city: str
    region: str
    employment_status: str
    marital_status: str
    dependents: int
    financial_goal_category: str
    risk_profile: str


@dataclass
class IncomeProfile:
    monthly_income: float
    other_income: float
    total_income: float
    stability: str
    annual_growth: float


@dataclass
class CategoryAmount:
    key: str
    name: str
    amount: float


@dataclass
class Debt:
    key: str
    name: str
    outstanding: float
    emi: float
    interest_rate: float
    tenure_months: int


@dataclass
class Goal:
    key: str
    name: str
    target_amount: float
    target_years: float
    priority: str


@dataclass
class GoalPlan:
    key: str
    name: str
    priority: str
    target_years: float
    future_cost: float
    monthly_required: float
    monthly_allocated: float
    funding_ratio: int
    status: str
    advice: str


@dataclass
class Allocation:
    safety: float
    debt_freedom: float
    goals: float
    wealth: float


@dataclass
class Projection:
    years: int
    contributed: float
    conservative: float
    expected: float


@dataclass
class Recommendation:
    category: str
    title: str
    detail: str
    impact: str


@dataclass
class RoadmapPhase:
    period: str
    title: str
    focus: str
    target: str


@dataclass
class ActionItem:
    action: str
    monthly_amount: float
    reason: str


@dataclass
class MilestoneProjection:
    name: str
    projected_date: str
    progress: int
    note: str


@dataclass
class CoachInsight:
    label: str
    title: str
    message: str


@dataclass
class PlanSummary:
    monthly_income: float
    monthly_expenses: float
    monthly_debt_emi: float
    monthly_surplus: float
    savings_ratio: float
    debt_ratio: float
    assets: float
    liabilities: float
    net_worth: float
    emergency_target: float
    emergency_fund: float
    emergency_progress: int
    health_score: int
    health_label: str
    score_reasons: List[str]
    coach_message: str
    wealth_stage: str
    allocation: Allocation
    goals: List[GoalPlan]
    projections: List[Projection]
    recommendations: List[Recommendation]
    expense_breakdown: List[CategoryAmount]
    asset_breakdown: List[CategoryAmount]
    debt_breakdown: List[Debt]
    roadmap: List[RoadmapPhase]
    action_plan: List[ActionItem]
    milestone_projections: List[MilestoneProjection]
    coach_insights: List[CoachInsight]
    assumptions: List[str] = field(default_factory=list)


@dataclass
class PlannerRecord:
    profile: Profile
    income: IncomeProfile
    expenses: List[CategoryAmount]
    investments: List[CategoryAmount]
    debts: List[Debt]
    selected_goals: List[Goal]
    summary: PlanSummary
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
