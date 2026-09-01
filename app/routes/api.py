import os
from flask import Blueprint, jsonify, request

from app.services.benchmark_service import BenchmarkService
from app.services.planner_service import PlannerService


api_bp = Blueprint("api", __name__, url_prefix="/api")

INTERNAL_TOKEN = os.getenv("INTERNAL_ENGINE_TOKEN", "3IiyWTTNW8jsRnDQrRcurSz9k1g_4aYmRMbpZ3XEUDipLQLJh")


def _check_internal_auth():
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {INTERNAL_TOKEN}"
    if auth_header != expected:
        return jsonify({"ok": False, "error": "Unauthorized internal API call"}), 401
    return None


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


# --- Public Gateway Routes (Proxies to OCI Engine or executes locally on OCI) ---

@api_bp.get("/strategy-lab/data")
def strategy_lab_data():
    try:
        from app.services.strategy_lab_service import StrategyLabService
        service = StrategyLabService()
        data = service.get_strategy_lab_data()
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "type": type(exc).__name__}), 503


@api_bp.post("/strategy-lab/approve")
def approve_strategy():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "candidate_id" not in payload:
        return jsonify({"ok": False, "error": "Missing or invalid candidate_id"}), 400

    candidate_id = str(payload.get("candidate_id", "")).strip()
    if not candidate_id:
        return jsonify({"ok": False, "error": "Missing or invalid candidate_id"}), 400

    from app.services.strategy_lab_service import StrategyLabService
    service = StrategyLabService()
    res, status_code = service.approve_strategy(candidate_id, source="WEB_PORTAL")
    return jsonify(res), status_code


@api_bp.post("/strategy-lab/import-algoverse")
def import_algoverse_backtest():
    payload = request.get_json(silent=True) or {}
    from app.services.strategy_lab_service import StrategyLabService
    service = StrategyLabService()
    res, status_code = service.import_algoverse_result(payload)
    return jsonify(res), status_code


@api_bp.post("/strategy-lab/telegram-webhook")
def telegram_webhook():
    payload = request.get_json(silent=True) or {}
    from app.services.strategy_lab_service import StrategyLabService
    service = StrategyLabService()
    res, status_code = service.handle_telegram_webhook(payload)
    return jsonify(res), status_code


# --- Internal Authenticated Routes (Executed directly on OCI VM) ---

@api_bp.get("/internal/strategy-lab/data")
def internal_strategy_lab_data():
    auth_err = _check_internal_auth()
    if auth_err:
        return auth_err
    from app.services.strategy_lab_service import StrategyLabService
    service = StrategyLabService()
    data = service.get_local_strategy_lab_data()
    return jsonify({"ok": True, "data": data})


@api_bp.post("/internal/strategy-lab/approve")
def internal_approve_strategy():
    auth_err = _check_internal_auth()
    if auth_err:
        return auth_err
    payload = request.get_json(silent=True) or {}
    candidate_id = str(payload.get("candidate_id", "")).strip()
    source = str(payload.get("source", "WEB_PORTAL"))
    if not candidate_id:
        return jsonify({"ok": False, "error": "Missing or invalid candidate_id"}), 400
    from app.services.strategy_lab_service import StrategyLabService
    service = StrategyLabService()
    res = service.local_approve_strategy(candidate_id, source=source)
    return jsonify(res), 200


@api_bp.post("/internal/strategy-lab/import-algoverse")
def internal_import_algoverse():
    auth_err = _check_internal_auth()
    if auth_err:
        return auth_err
    payload = request.get_json(silent=True) or {}
    from app.services.strategy_lab_service import StrategyLabService
    service = StrategyLabService()
    res = service.local_import_algoverse_result(payload)
    return jsonify(res), 200


@api_bp.post("/internal/strategy-lab/telegram-webhook")
def internal_telegram_webhook():
    auth_err = _check_internal_auth()
    if auth_err:
        return auth_err
    payload = request.get_json(silent=True) or {}
    callback_query = payload.get("callback_query", {})
    callback_data = callback_query.get("data", "")
    if callback_data:
        from engine.notifier import handle_telegram_callback
        from app.services.strategy_lab_service import MULTIBAGGER_DB
        msg = handle_telegram_callback(callback_data, MULTIBAGGER_DB)
        return jsonify({"ok": True, "result": msg}), 200
    return jsonify({"ok": True, "result": "No callback data."}), 200
