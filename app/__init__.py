import os
import base64
import hmac
import hashlib
import json
import time
from flask import Flask, render_template, request, redirect, jsonify

def verify_token(token, secret, max_age_seconds=300):
    if token.startswith("v1."):
        return verify_portal_token(token, secret, max_age_seconds)

    return verify_legacy_token(token, secret, max_age_seconds)

def verify_portal_token(token, secret, max_age_seconds):
    try:
        version, encoded_payload, signature = token.split(".")
        if version != "v1":
            return False

        expected_signature = hmac.new(
            secret.encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return False

        padding = "=" * (-len(encoded_payload) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + padding))
        issued_at = int(payload["issuedAt"]) / 1000.0
        return (
            payload.get("appId") == "money-planner"
            and 0 <= time.time() - issued_at <= max_age_seconds
        )
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False

def verify_legacy_token(token, secret, max_age_seconds):
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False
        username, timestamp_str, signature = parts
        
        # Verify timestamp is within max_age_seconds
        timestamp = int(timestamp_str) / 1000.0
        current_time = time.time()
        if abs(current_time - timestamp) > max_age_seconds:
            return False
            
        # Re-sign
        payload = f"{username}:{timestamp_str}"
        expected_signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False

def redirect_to_login():
    host = request.headers.get("Host", "")
    if "localhost" in host or "127.0.0.1" in host:
        return redirect("http://localhost:5173/?error=unauthorized")
    portal_url = os.environ.get("LIVEUNLOAN_URL", "https://liveunloan.vercel.app").rstrip("/")
    return redirect(f"{portal_url}/?error=unauthorized")

def create_app():
    from app.config import Config
    from app.routes.api import api_bp

    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    app.register_blueprint(api_bp)

    @app.before_request
    def check_auth():
        # Exclude static assets, health checks, testing mode, and local dev preview
        import sys
        local_preview = os.environ.get("LOCAL_PREVIEW", "").lower() in ("1", "true", "yes")
        if local_preview or app.config.get("TESTING") or app.testing or "unittest" in sys.modules or request.path.startswith("/static") or request.path == "/api/health":
            return None

        secret = os.environ.get("SHARED_SESSION_SECRET", "fallback_secret_for_local_dev")

        # 1. Check for token in query parameters
        token = request.args.get("token")
        if token:
            if verify_token(token, secret, 300):
                # Valid token! Redirect to clean URL and set session cookie
                resp = redirect(request.path)
                resp.set_cookie(
                    "unloan_money_session",
                    token,
                    max_age=86400, # 1 day
                    httponly=True,
                    secure=request.is_secure or request.headers.get("X-Forwarded-Proto", "http") == "https",
                    samesite="Lax"
                )
                return resp
            else:
                return redirect_to_login()

        # 2. Check for existing session cookie
        session_cookie = request.cookies.get("unloan_money_session")
        if session_cookie:
            if verify_token(session_cookie, secret, 86400):
                return None

        # 3. Unauthorized fallback
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
            
        return redirect_to_login()

    @app.get("/")
    def home():
        return render_template("index.html")

    return app
