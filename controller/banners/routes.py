import os
import uuid
from flask import Blueprint, request, g
from db import query
from errors import success_response, AppError
from middleware.admin_required import admin_required
from config import Config

banners_bp = Blueprint("banners_public", __name__, url_prefix="/api/v1/banners")


@banners_bp.route("", methods=["GET"])
def list_banners():
    """Public: return all active banners ordered by sort_order."""
    banners = query(
        "SELECT id, image_url, title, subtitle, link, sort_order FROM banners WHERE is_active = 1 ORDER BY sort_order ASC"
    )
    return success_response("Banners fetched", banners)


# ── Admin banner routes (same file, different blueprint prefix) ──────────────
admin_banners_bp = Blueprint("banners_admin", __name__, url_prefix="/api/v1/admin/banners")

ALLOWED = {"jpg", "jpeg", "png", "webp"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@admin_banners_bp.route("", methods=["GET"])
@admin_required
def admin_list_banners():
    banners = query(
        "SELECT id, image_url, title, subtitle, link, is_active, sort_order FROM banners ORDER BY sort_order ASC"
    )
    return success_response("Banners fetched", banners)


@admin_banners_bp.route("", methods=["POST"])
@admin_required
def create_banner():
    if "image" not in request.files:
        raise AppError("image file is required", 400)

    file = request.files["image"]
    if not file or not _allowed(file.filename):
        raise AppError("Invalid image type. Allowed: jpg, jpeg, png, webp", 400)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"banner_{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    file.save(save_path)

    image_url = f"/uploads/{filename}"
    title      = request.form.get("title", "")
    subtitle   = request.form.get("subtitle", "")
    link       = request.form.get("link", "")
    sort_order = int(request.form.get("sort_order", 0))

    query(
        "INSERT INTO banners (image_url, title, subtitle, link, sort_order) VALUES (%s, %s, %s, %s, %s)",
        (image_url, title, subtitle, link, sort_order),
        commit=True,
    )
    return success_response("Banner created", {"image_url": image_url}, 201)


@admin_banners_bp.route("/<int:banner_id>", methods=["DELETE"])
@admin_required
def delete_banner(banner_id):
    banner = query("SELECT id, image_url FROM banners WHERE id = %s", (banner_id,), fetchone=True)
    if not banner:
        raise AppError("Banner not found", 404)

    # Remove physical file
    try:
        path = os.path.join(Config.UPLOAD_FOLDER, os.path.basename(banner["image_url"]))
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

    query("DELETE FROM banners WHERE id = %s", (banner_id,), commit=True)
    return success_response("Banner deleted")


@admin_banners_bp.route("/<int:banner_id>/toggle", methods=["PATCH"])
@admin_required
def toggle_banner(banner_id):
    banner = query("SELECT id, is_active FROM banners WHERE id = %s", (banner_id,), fetchone=True)
    if not banner:
        raise AppError("Banner not found", 404)
    new_state = 0 if banner["is_active"] else 1
    query("UPDATE banners SET is_active = %s WHERE id = %s", (new_state, banner_id), commit=True)
    return success_response("Banner toggled", {"is_active": bool(new_state)})
