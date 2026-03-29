import os
from dotenv import load_dotenv

# Always load .env from the backend root, regardless of CWD
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

class Config:
    # ── Database ─────────────────────────────────────────────
    DB_HOST     = os.getenv("DB_HOST") or "localhost"
    DB_PORT     = int(os.getenv("DB_PORT") or 3306)
    DB_NAME     = os.getenv("DB_NAME") or "tazaura_db"
    DB_USER     = os.getenv("DB_USER") or "root"
    DB_PASSWORD = os.getenv("DB_PASSWORD") or "852456"

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET          = os.getenv("JWT_SECRET", "change_me_in_production")
    JWT_EXPIRY_HOURS    = int(os.getenv("JWT_EXPIRY_HOURS", 24))

    # ── Razorpay ─────────────────────────────────────────────
    RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

    # ── Upload ───────────────────────────────────────────────
    UPLOAD_FOLDER       = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH  = 5 * 1024 * 1024   # 5 MB
    ALLOWED_EXTENSIONS  = {"jpg", "jpeg", "png", "webp"}
