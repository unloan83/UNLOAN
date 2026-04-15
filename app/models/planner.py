from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class UserProfile:
    name: str
    age: int
    mobile: str
    dependents: int
    marital_status: str
    has_health_insurance: bool
    has_term_insurance: bool


@dataclass
class FinancialInput:
    mode: str
    income: float
    rent: float
    food: float
    misc: float


@dataclass
class Milestone:
    key: str
    name: str
    amount: float
    years: float


@dataclass
class PlanAllocation:
    insurance: float
    short_term: float
    long_term: float


@dataclass
class PlanSummary:
    surplus: float
    health_score: int
    health_note: str
    insurance_target: float
    allocation: PlanAllocation
    notes: List[str] = field(default_factory=list)


@dataclass
class PlannerRecord:
    profile: UserProfile
    financial: FinancialInput
    milestones: List[Milestone]
    summary: PlanSummary
    consult: bool
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
