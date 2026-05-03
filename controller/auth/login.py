from flask import request
import bcrypt
from controller.auth.captcha import validate_captcha
from db import query
from errors import AppError, success_response
from helper.jwt import generate_token


def login_user():
    """POST /api/v1/auth/login"""
    data = request.get_json(silent=True) or {}
    required = ["username", "password", "captcha_id", "captcha_code"]
    for field in required:
        if not data.get(field):
            raise AppError(f"'{field}' is required", 400)

    validate_captcha(data["captcha_id"], data["captcha_code"])

    user = query(
        "SELECT id, name, username, email, password, role FROM users WHERE username = %s AND is_active = 1",
        (data["username"],), fetchone=True,
    )
    if not user or not bcrypt.checkpw(data["password"].encode("utf-8"), user["password"].encode("utf-8")):
        raise AppError("Invalid username or password", 401)

    token = generate_token(user["id"], user["role"])

    return success_response("Login successful", {
        "token": token,
        "user": {
            "id":       user["id"],
            "name":     user["name"],
            "username": user["username"],
            "email":    user["email"],
            "role":     user["role"],
        },
    })
