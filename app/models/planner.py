from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class UserProfile:
    name: str
    age: int
    location: str
    dependents: int
    marital_status: str
    has_health_insurance: bool
    has_term_insurance: bool
    risk_profile: str
    retirement_age: int


@dataclass
class FinancialInput:
    mode: str
    income: float
    rent: float
    food: float
    misc: float
    debt_emi: float
    current_savings: float
    current_investments: float


@dataclass
class Milestone:
    key: str
    name: str
    amount: float
    years: float


@dataclass
class GoalRecommendation:
    key: str
    name: str
    years: float
    future_cost: float
    monthly_required: float
    monthly_allocated: float
    funding_ratio: int
    status: str
    recommendation: str


@dataclass
class PlanAllocation:
    emergency: float
    protection: float
    milestones: float
    retirement: float


@dataclass
class Projection:
    years: int
    invested: float
    projected_value: float


@dataclass
class PlanSummary:
    surplus: float
    savings_ratio: float
    debt_ratio: float
    health_score: int
    health_note: str
    emergency_target: float
    emergency_gap: float
    insurance_target: float
    allocation: PlanAllocation
    goals: List[GoalRecommendation]
    projections: List[Projection]
    next_steps: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)


@dataclass
class PlannerRecord:
    profile: UserProfile
    financial: FinancialInput
    milestones: List[Milestone]
    summary: PlanSummary
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
