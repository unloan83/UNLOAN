import unittest

from app import create_app
from app.services.planner_service import PlannerService


def valid_payload(**overrides):
    payload = {
        "name": "Asha",
        "age": 32,
        "retirementAge": 60,
        "location": "metro",
        "dependents": 1,
        "maritalStatus": "married",
        "hasHealthInsurance": True,
        "hasTermInsurance": True,
        "riskProfile": "balanced",
        "inputMode": "monthly",
        "income": 120000,
        "rent": 30000,
        "food": 18000,
        "misc": 12000,
        "debtEmi": 10000,
        "currentSavings": 300000,
        "currentInvestments": 500000,
        "milestones": [
            {"key": "home", "name": "Home", "amount": 2500000, "years": 8}
        ],
    }
    payload.update(overrides)
    return payload


class PlannerServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = PlannerService()

    def test_builds_actionable_plan(self):
        record = self.service.generate(valid_payload())
        self.assertEqual(record.summary.surplus, 50000)
        self.assertEqual(record.summary.savings_ratio, 41.7)
        self.assertGreater(record.summary.emergency_target, 0)
        self.assertEqual(len(record.summary.goals), 1)
        self.assertGreater(record.summary.goals[0].future_cost, 2500000)
        self.assertGreater(record.summary.projections[-1].projected_value, record.summary.projections[-1].invested)

    def test_yearly_inputs_are_normalized(self):
        payload = valid_payload(
            inputMode="yearly",
            income=1440000,
            rent=360000,
            food=216000,
            misc=144000,
            debtEmi=120000,
        )
        record = self.service.generate(payload)
        self.assertEqual(record.financial.income, 120000)
        self.assertEqual(record.summary.surplus, 50000)

    def test_rejects_negative_cash_flow(self):
        with self.assertRaisesRegex(ValueError, "exceed income"):
            self.service.generate(valid_payload(income=50000, rent=45000, food=10000))

    def test_dependent_without_term_cover_gets_protection_action(self):
        record = self.service.generate(valid_payload(hasTermInsurance=False))
        self.assertGreater(record.summary.allocation.protection, 0)
        self.assertTrue(any("term cover" in step for step in record.summary.next_steps))

    def test_age_reduces_assumed_return_near_retirement(self):
        record = self.service.generate(valid_payload(age=58, retirementAge=63, riskProfile="growth"))
        self.assertIn("8%", record.summary.assumptions[0])
        self.assertIn(5, [item.years for item in record.summary.projections])


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

    def test_invalid_json_is_reported(self):
        response = self.client.post("/api/plan/generate", data="not-json", content_type="application/json")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
