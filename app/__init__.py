from flask import Flask, render_template

from app.config import Config
from app.routes.api import api_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    app.register_blueprint(api_bp)

    @app.get("/")
    def home():
        return render_template("index.html")

    return app
