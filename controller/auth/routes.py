from flask import Blueprint
from controller.auth.captcha import generate_captcha
from controller.auth.register import register_user
from controller.auth.login import login_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

auth_bp.route("/captcha", methods=["POST"])(generate_captcha)
auth_bp.route("/register", methods=["POST"])(register_user)
auth_bp.route("/login", methods=["POST"])(login_user)
