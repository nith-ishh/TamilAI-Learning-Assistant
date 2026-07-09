"""
TamilAI Learning Assistant - Flask Backend
Main application entry point
"""

from flask import Flask
from flask_cors import CORS
from database.db import init_db
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.quiz import quiz_bp
from routes.notes import notes_bp
from routes.upload import upload_bp
from routes.progress import progress_bp
import os
from dotenv import load_dotenv
load_dotenv()

def create_app():
    app = Flask(__name__)

    # ── Config ──────────────────────────────────────────
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tamilai-secret-change-in-production')
    app.config['JWT_EXPIRY_HOURS'] = 24
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── CORS ─────────────────────────────────────────────
    from flask_cors import CORS

    CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://127.0.0.1:5500",
                "http://localhost:5500",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://localhost:3000"
            ]
        }
    },
    supports_credentials=True
)

    # ── Database ──────────────────────────────────────────
    init_db()

        # ── Blueprints ────────────────────────────────────────
    app.register_blueprint(auth_bp,     url_prefix='/api/auth')
    app.register_blueprint(chat_bp,     url_prefix='/api/chat')
    app.register_blueprint(quiz_bp,     url_prefix='/api/quiz')
    app.register_blueprint(notes_bp,    url_prefix='/api/notes')
    app.register_blueprint(upload_bp,   url_prefix='/api/upload')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')

    # Root route
    @app.get("/")
    def home():
        return {
            "status": "ok",
            "message": "TamilAI Backend is Running 🚀"
        }

    # Health check
    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "message": "TamilAI API is running"
        }

    return app


if __name__ == "__main__":
    app = create_app()

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )