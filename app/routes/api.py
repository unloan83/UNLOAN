from flask import Blueprint, jsonify, request

from app.services.benchmark_service import BenchmarkService
from app.services.planner_service import PlannerService


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.post("/plan/generate")
def generate_plan():
    planner = PlannerService()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "Send a valid JSON request."}), 400
    try:
        record = planner.generate(payload)
        return jsonify({"ok": True, "record": record.to_dict()})
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@api_bp.post("/benchmarks/context")
def benchmark_context():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "Send a valid JSON request."}), 400
    return jsonify({"ok": True, "benchmark": BenchmarkService().context(payload)})


@api_bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "unloan-moneyview"})
