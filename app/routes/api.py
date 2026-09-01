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


@api_bp.get("/strategy-lab/data")
def strategy_lab_data():
    try:
        from app.services.strategy_lab_service import StrategyLabService
        service = StrategyLabService()
        data = service.get_strategy_lab_data()
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "type": type(exc).__name__}), 500


@api_bp.post("/strategy-lab/approve")
def approve_strategy():
    from app.services.strategy_lab_service import StrategyLabService
    payload = request.get_json(silent=True) or {}
    candidate_id = payload.get("candidate_id", "NOTRADE")
    service = StrategyLabService()
    res = service.approve_strategy(candidate_id, source="WEB_PORTAL")
    return jsonify(res)


@api_bp.post("/strategy-lab/import-algoverse")
def import_algoverse_backtest():
    from app.services.strategy_lab_service import StrategyLabService
    payload = request.get_json(silent=True) or {}
    service = StrategyLabService()
    res = service.import_algoverse_result(payload)
    return jsonify(res)


@api_bp.post("/strategy-lab/telegram-webhook")
def telegram_webhook():
    from engine.notifier import handle_telegram_callback
    payload = request.get_json(silent=True) or {}
    callback_query = payload.get("callback_query", {})
    callback_data = callback_query.get("data", "")
    if callback_data:
        from app.services.strategy_lab_service import MULTIBAGGER_DB
        msg = handle_telegram_callback(callback_data, MULTIBAGGER_DB)
        return jsonify({"ok": True, "result": msg})
    return jsonify({"ok": True, "result": "No callback data."})
