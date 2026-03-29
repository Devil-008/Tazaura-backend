from functools import wraps
from flask import request
from helper.jwt import decode_token
from errors import AppError
import jwt


def auth_required(f):
    """Decorator: validates Bearer JWT and injects g.user_id / g.user_role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AppError("Authentication required", 401)
        token = auth_header.split(" ", 1)[1]
        try:
            from flask import g
            payload = decode_token(token)
            g.user_id   = payload["sub"]
            g.user_role = payload["role"]
        except jwt.ExpiredSignatureError:
            raise AppError("Token has expired. Please login again.", 401)
        except jwt.InvalidTokenError:
            raise AppError("Invalid token. Please login again.", 401)
        return f(*args, **kwargs)
    return decorated
