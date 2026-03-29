from functools import wraps
from flask import g
from middleware.auth_required import auth_required
from errors import AppError


def admin_required(f):
    """Stacks on top of auth_required; additionally asserts role == 'admin'."""
    @wraps(f)
    @auth_required
    def decorated(*args, **kwargs):
        if g.user_role != "admin":
            raise AppError("Admin access required", 403)
        return f(*args, **kwargs)
    return decorated
