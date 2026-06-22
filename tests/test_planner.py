import unittest

from app import create_app
from app.services.benchmark_service import BenchmarkService
from app.services.planner_service import PlannerService


def valid_payload(**overrides):
    payload = {
        "profile": {
            "name": "Asha", "age": 32, "city": "Pune", "region": "urban",
            "employmentStatus": "salaried", "maritalStatus": "married", "dependents": 1,
            "financialGoalCategory": "wealth", "riskProfile": "balanced"
        },
        "income": {"monthlyIncome": 120000, "otherIncome": 10000, "stability": "stable", "annualGrowth": 6},
        "expenses": [
            {"key": "rent", "name": "House rent", "amount": 30000},
            {"key": "food", "name": "Food", "amount": 18000},
            {"key": "lifestyle", "name": "Lifestyle", "amount": 12000}
        ],
        "investments": [
            {"key": "emergency_fund", "name": "Emergency fund", "amount": 300000},
            {"key": "mutual_funds", "name": "Mutual funds", "amount": 500000}
        ],
        "debts": [{"key": "vehicle_loan", "name": "Vehicle loan", "outstanding": 300000, "emi": 10000, "interestRate": 9, "tenureMonths": 30}],
        "goals": [{"key": "buy_house", "name": "Buy a house", "targetAmount": 2500000, "targetYears": 8, "priority": "high"}]
    }
    payload.update(overrides)
    return payload


class PlannerServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = PlannerService()

    def test_builds_dynamic_personalized_plan(self):
        record = self.service.generate(valid_payload())
        self.assertEqual(record.summary.monthly_surplus, 60000)
        self.assertEqual(record.summary.savings_ratio, 46.2)
        self.assertEqual(len(record.summary.goals), 1)
        self.assertGreater(record.summary.goals[0].future_cost, 2500000)
        self.assertEqual(len(record.summary.roadmap), 5)
        self.assertGreaterEqual(len(record.summary.action_plan), 2)
        self.assertEqual(len(record.summary.coach_insights), 5)
        self.assertTrue(record.summary.score_reasons)

    def test_only_selected_categories_are_counted(self):
        record = self.service.generate(valid_payload(expenses=[{"key": "food", "name": "Food", "amount": 20000}], debts=[]))
        self.assertEqual(record.summary.monthly_expenses, 20000)
        self.assertEqual(record.summary.monthly_debt_emi, 0)

    def test_rejects_negative_cash_flow(self):
        payload = valid_payload(expenses=[{"key": "rent", "name": "Rent", "amount": 140000}])
        with self.assertRaisesRegex(ValueError, "higher than income"):
            self.service.generate(payload)

    def test_high_cost_debt_is_prioritized(self):
        payload = valid_payload(debts=[{"key": "credit_card", "name": "Card", "outstanding": 200000, "emi": 8000, "interestRate": 36, "tenureMonths": 24}])
        record = self.service.generate(payload)
        self.assertGreater(record.summary.allocation.debt_freedom, 0)
        self.assertTrue(any("expensive debt" in item.title.lower() for item in record.summary.recommendations))

    def test_irregular_income_increases_safety_target(self):
        stable = self.service.generate(valid_payload())
        variable_payload = valid_payload()
        variable_payload["income"] = {**variable_payload["income"], "stability": "variable"}
        variable = self.service.generate(variable_payload)
        self.assertGreater(variable.summary.emergency_target, stable.summary.emergency_target)


class BenchmarkTests(unittest.TestCase):
    def test_benchmark_is_explicitly_estimated_and_profile_aware(self):
        service = BenchmarkService()
        result = service.context({"age": 40, "region": "metro", "employmentStatus": "freelance", "dependents": 2, "monthlyIncome": 100000})
        self.assertIn("Estimated", result["metadata"]["label"])
        self.assertGreater(result["ranges"]["emergency_months"][1], 6)
        self.assertGreater(result["ranges"]["rent_share_percent"][0], 20)

    def test_benchmark_calculates_contextual_actuals(self):
        result = BenchmarkService().context({"monthlyIncome": 100000, "monthlyExpenses": 50000, "rent": 25000, "monthlyEmi": 10000, "liquidSavings": 300000})
        self.assertEqual(result["actuals"]["rent_share_percent"], 25)
        self.assertEqual(result["actuals"]["emi_share_percent"], 10)


class ApiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.client = create_app().test_client()
        except ModuleNotFoundError as exc:
            if exc.name == "flask":
                self.skipTest("Flask dependency is validated in the deployment build")
            raise

    def test_generate_endpoint(self):
        response = self.client.post("/api/plan/generate", json=valid_payload())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

    def test_benchmark_endpoint(self):
        response = self.client.post("/api/benchmarks/context", json={"age": 30, "monthlyIncome": 80000})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()
