from flask import Blueprint, request, g
from db import query
from errors import AppError, success_response
from middleware.auth_required import auth_required
import bcrypt

profile_bp = Blueprint("profile", __name__, url_prefix="/api/v1/profile")


@profile_bp.route("", methods=["GET"])
@auth_required
def get_profile():
    user = query(
        "SELECT id, name, username, email, role, created_at FROM users WHERE id = %s",
        (g.user_id,), fetchone=True,
    )
    addresses = query("SELECT * FROM addresses WHERE user_id = %s", (g.user_id,))
    user["addresses"] = addresses
    return success_response("Profile fetched", user)


@profile_bp.route("", methods=["PUT"])
@auth_required
def update_profile():
    data = request.get_json(silent=True) or {}
    sets, vals = [], []
    for field in ["name", "email"]:
        if field in data:
            sets.append(f"{field} = %s")
            vals.append(data[field])
    if "password" in data and data["password"]:
        sets.append("password = %s")
        vals.append(bcrypt.hashpw(data["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8"))
    if not sets:
        raise AppError("Nothing to update", 400)
    vals.append(g.user_id)
    query(f"UPDATE users SET {', '.join(sets)} WHERE id = %s", tuple(vals), commit=True)
    return success_response("Profile updated")


# ── Addresses ───────────────────────────────────────────────────────────────
@profile_bp.route("/addresses", methods=["POST"])
@auth_required
def add_address():
    data = request.get_json(silent=True) or {}
    required = ["full_name", "phone", "line1", "city", "state", "pincode"]
    for f in required:
        if not data.get(f):
            raise AppError(f"'{f}' is required", 400)

    if data.get("is_default"):
        query("UPDATE addresses SET is_default=0 WHERE user_id=%s", (g.user_id,), commit=True)

    aid = query(
        """INSERT INTO addresses (user_id, label, full_name, phone, line1, line2, city, state, pincode, is_default)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (g.user_id, data.get("label","Home"), data["full_name"], data["phone"],
         data["line1"], data.get("line2",""), data["city"], data["state"],
         data["pincode"], int(bool(data.get("is_default", 0)))),
        commit=True,
    )
    return success_response("Address added", {"address_id": aid}, 201)


@profile_bp.route("/addresses/<int:aid>", methods=["DELETE"])
@auth_required
def delete_address(aid):
    addr = query("SELECT id FROM addresses WHERE id=%s AND user_id=%s", (aid, g.user_id), fetchone=True)
    if not addr:
        raise AppError("Address not found", 404)
    query("DELETE FROM addresses WHERE id=%s", (aid,), commit=True)
    return success_response("Address deleted")
