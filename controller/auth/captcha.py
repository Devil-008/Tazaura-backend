import uuid
import string
import random
from datetime import datetime, timedelta, timezone
from db import query
from errors import AppError, success_response, error_response
from flask import request


def generate_captcha():
    """POST /api/v1/auth/captcha  – returns captcha_id + code (dev) or image (prod)"""
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=6))
    captcha_id = str(uuid.uuid4())
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    query(
        "INSERT INTO captcha (id, code, expiry_time) VALUES (%s, %s, %s)",
        (captcha_id, code, expiry),
        commit=True,
    )
    # In production you would return an image; for dev we return the code directly
    return success_response("Captcha generated", {
        "captcha_id": captcha_id,
        "code": code,          # Remove this in production!
    }, 201)


def validate_captcha(captcha_id: str, code: str):
    """Internal helper called by register/login. Raises AppError on failure."""
    row = query(
        "SELECT code, expiry_time, used FROM captcha WHERE id = %s",
        (captcha_id,), fetchone=True,
    )
    if not row:
        raise AppError("Invalid captcha ID", 400)
    if row["used"]:
        raise AppError("Captcha already used", 400)
    if datetime.now(timezone.utc) > row["expiry_time"].replace(tzinfo=timezone.utc):
        raise AppError("Captcha has expired", 400)
    if row["code"].upper() != code.upper():
        raise AppError("Incorrect captcha code", 400)
    # Mark as used
    query("UPDATE captcha SET used = 1 WHERE id = %s", (captcha_id,), commit=True)
