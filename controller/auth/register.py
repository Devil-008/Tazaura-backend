from flask import request
import bcrypt
from controller.auth.captcha import validate_captcha
from db import query
from errors import AppError, success_response


def register_user():
    """POST /api/v1/auth/register"""
    data = request.get_json(silent=True) or {}
    required = ["name", "username", "email", "password", "captcha_id", "captcha_code"]
    for field in required:
        if not data.get(field):
            raise AppError(f"'{field}' is required", 400)

    validate_captcha(data["captcha_id"], data["captcha_code"])

    # Check duplicates
    if query("SELECT id FROM users WHERE username = %s", (data["username"],), fetchone=True):
        raise AppError("Username already taken", 409)
    if query("SELECT id FROM users WHERE email = %s", (data["email"],), fetchone=True):
        raise AppError("Email already registered", 409)

    hashed_pw = bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user_id = query(
        "INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)",
        (data["name"], data["username"], data["email"], hashed_pw),
        commit=True,
    )
    return success_response("Registration successful", {"user_id": user_id}, 201)
