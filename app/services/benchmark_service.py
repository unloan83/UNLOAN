import json
from pathlib import Path
from typing import Any, Dict


class BenchmarkService:
    def __init__(self, config_path: str | None = None):
        path = Path(config_path) if config_path else Path(__file__).resolve().parents[2] / "data" / "benchmarks.json"
        self.config = json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _number(payload: Dict[str, Any], key: str, default: float = 0) -> float:
        try:
            return max(float(payload.get(key, default) or 0), 0)
        except (TypeError, ValueError):
            return default

    def context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        age = int(self._number(payload, "age", 30))
        income = self._number(payload, "monthlyIncome") + self._number(payload, "otherIncome")
        region = str(payload.get("region", "urban"))
        employment = str(payload.get("employmentStatus", "salaried"))
        dependents = int(self._number(payload, "dependents"))
        expenses = self._number(payload, "monthlyExpenses")
        rent = self._number(payload, "rent")
        emi = self._number(payload, "monthlyEmi")
        liquid_savings = self._number(payload, "liquidSavings")

        base = self.config["base"]
        savings_low, savings_high = base["savings_rate_percent"]
        rent_low, rent_high = base["rent_share_percent"]
        emergency_low, emergency_high = base["emergency_months"]

        age_rule = next((row for row in self.config["age_groups"] if row["min"] <= age <= row["max"]), self.config["age_groups"][1])
        income_rule = next((row for row in self.config["income_bands"] if income <= row["max_monthly_income"]), self.config["income_bands"][-1])
        family_rule = self.config["family_status"]["with_dependents" if dependents else "no_dependents"]
        region_rule = self.config["regions"].get(region, {})
        employment_rule = self.config["employment_types"].get(employment, {})

        savings_adjustment = age_rule.get("savings_rate_adjustment", 0) + income_rule.get("savings_rate_adjustment", 0) + family_rule.get("savings_rate_adjustment", 0)
        rent_adjustment = region_rule.get("rent_share_adjustment", 0)
        emergency_adjustment = age_rule.get("emergency_months_adjustment", 0) + family_rule.get("emergency_months_adjustment", 0) + employment_rule.get("emergency_months_adjustment", 0)

        savings_range = [max(savings_low + savings_adjustment, 5), min(savings_high + savings_adjustment, 45)]
        rent_range = [max(rent_low + rent_adjustment, 10), min(rent_high + rent_adjustment, 45)]
        emergency_range = [min(emergency_low + emergency_adjustment, 12), min(emergency_high + emergency_adjustment, 15)]
        emi_max = base["healthy_emi_max_percent"]

        actual_savings_rate = ((income - expenses - emi) / income * 100) if income else None
        actual_rent_share = (rent / income * 100) if income else None
        actual_emi_share = (emi / income * 100) if income else None
        actual_emergency_months = (liquid_savings / expenses) if expenses else None

        return {
            "metadata": self.config["metadata"],
            "profile": {"age_group": f"{age_rule['min']}–{age_rule['max']}", "region": region, "employment": employment},
            "ranges": {
                "savings_rate_percent": savings_range,
                "rent_share_percent": rent_range,
                "healthy_emi_max_percent": emi_max,
                "emergency_months": emergency_range,
                "monthly_savings_amount": [round(income * savings_range[0] / 100), round(income * savings_range[1] / 100)] if income else [0, 0]
            },
            "actuals": {
                "savings_rate_percent": round(actual_savings_rate, 1) if actual_savings_rate is not None else None,
                "rent_share_percent": round(actual_rent_share, 1) if actual_rent_share is not None else None,
                "emi_share_percent": round(actual_emi_share, 1) if actual_emi_share is not None else None,
                "emergency_months": round(actual_emergency_months, 1) if actual_emergency_months is not None else None
            }
        }
