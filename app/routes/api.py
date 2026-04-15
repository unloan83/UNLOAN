from flask import Blueprint, current_app, jsonify, request

from app.services.planner_service import PlannerService
from app.services.storage_service import LocalStorageService
from app.services.auth_service import AuthService

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.post("/plan/generate")
def generate_plan():
    planner = PlannerService()
    payload = request.get_json(force=True)
    try:
        record = planner.generate(payload)
        return jsonify({"ok": True, "record": record.to_dict()})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@api_bp.post("/plan/save")
def save_plan():
    payload = request.get_json(force=True)
    storage = LocalStorageService(current_app.config["STORAGE_PATH"])
    storage.save(payload)
    return jsonify({"ok": True})


@api_bp.post("/admin/login")
def admin_login():
    payload = request.get_json(force=True)
    auth = AuthService(
        secret_key=current_app.config["SECRET_KEY"],
        admin_username=current_app.config["ADMIN_USERNAME"],
        admin_password_hash=current_app.config["ADMIN_PASSWORD_HASH"],
    )
    token = auth.login(payload.get("username", ""), payload.get("password", ""))
    if not token:
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401
    return jsonify({"ok": True, "token": token})


@api_bp.get("/admin/plans")
def admin_plans():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()

    auth = AuthService(
        secret_key=current_app.config["SECRET_KEY"],
        admin_username=current_app.config["ADMIN_USERNAME"],
        admin_password_hash=current_app.config["ADMIN_PASSWORD_HASH"],
    )

    if not auth.verify_token(token, current_app.config["TOKEN_MAX_AGE_SECONDS"]):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    storage = LocalStorageService(current_app.config["STORAGE_PATH"])
    return jsonify({"ok": True, "records": storage.list_all()})
