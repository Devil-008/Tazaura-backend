import os
from flask import Blueprint, request, g, current_app, send_from_directory
from db import query
from errors import AppError, success_response
from middleware.auth_required import auth_required
from middleware.admin_required import admin_required
from config import Config

products_bp = Blueprint("products", __name__, url_prefix="/api/v1")


# ── Public: list & filter products ─────────────────────────────────────────
@products_bp.route("/products", methods=["GET"])
def list_products():
    category   = request.args.get("category", "")
    search     = request.args.get("search", "")
    page       = max(1, int(request.args.get("page", 1)))
    per_page   = min(50, int(request.args.get("per_page", 12)))
    offset     = (page - 1) * per_page

    conditions = ["p.is_active = 1"]
    params = []
    if category:
        conditions.append("p.category = %s")
        params.append(category)
    if search:
        conditions.append("(p.name LIKE %s OR p.description LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = " AND ".join(conditions)

    total = query(f"SELECT COUNT(*) AS cnt FROM products p WHERE {where}", tuple(params), fetchone=True)["cnt"]

    params_page = params + [per_page, offset]
    rows = query(
        f"""SELECT p.id, p.name, p.slug, p.category, p.price, p.mrp, p.stock,
                   p.unit, p.is_featured,
                   (SELECT image_url FROM product_images pi WHERE pi.product_id = p.id AND pi.is_primary = 1 LIMIT 1) AS image
            FROM products p
            WHERE {where}
            ORDER BY p.is_featured DESC, p.created_at DESC
            LIMIT %s OFFSET %s""",
        tuple(params_page),
    )
    return success_response("Products fetched", {
        "products": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": -(-total // per_page),
    })


# ── Public: single product detail ──────────────────────────────────────────
@products_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = query(
        "SELECT * FROM products WHERE id = %s AND is_active = 1",
        (product_id,), fetchone=True,
    )
    if not product:
        raise AppError("Product not found", 404)

    images = query(
        "SELECT id, image_url, is_primary FROM product_images WHERE product_id = %s ORDER BY sort_order",
        (product_id,),
    )
    reviews = query(
        """SELECT r.id, r.rating, r.comment, r.created_at, u.name AS reviewer
           FROM reviews r JOIN users u ON u.id = r.user_id
           WHERE r.product_id = %s ORDER BY r.created_at DESC LIMIT 20""",
        (product_id,),
    )
    avg_rating = query(
        "SELECT AVG(rating) AS avg_rating, COUNT(*) AS total FROM reviews WHERE product_id = %s",
        (product_id,), fetchone=True,
    )
    product["images"]     = images
    product["reviews"]    = reviews
    product["avg_rating"] = float(avg_rating["avg_rating"] or 0)
    product["review_count"] = avg_rating["total"]
    return success_response("Product fetched", product)


# ── Public: categories list ─────────────────────────────────────────────────
@products_bp.route("/categories", methods=["GET"])
def list_categories():
    rows = query(
        "SELECT DISTINCT category, COUNT(*) AS count FROM products WHERE is_active = 1 GROUP BY category",
    )
    return success_response("Categories fetched", rows)


# ── Auth: add review ────────────────────────────────────────────────────────
@products_bp.route("/products/<int:product_id>/reviews", methods=["POST"])
@auth_required
def add_review(product_id):
    data = request.get_json(silent=True) or {}
    rating  = data.get("rating")
    comment = data.get("comment", "")
    if not rating or not (1 <= int(rating) <= 5):
        raise AppError("Rating must be between 1 and 5", 400)

    existing = query(
        "SELECT id FROM reviews WHERE user_id = %s AND product_id = %s",
        (g.user_id, product_id), fetchone=True,
    )
    if existing:
        raise AppError("You already reviewed this product", 409)

    query(
        "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (%s, %s, %s, %s)",
        (product_id, g.user_id, int(rating), comment), commit=True,
    )
    return success_response("Review added", {}, 201)


# ── Admin: add product ──────────────────────────────────────────────────────
@products_bp.route("/admin/products", methods=["POST"])
@admin_required
def admin_add_product():
    data = request.get_json(silent=True) or {}
    required = ["name", "category", "price", "stock"]
    for f in required:
        if data.get(f) is None or str(data.get(f)).strip() == "":
            raise AppError(f"'{f}' is required", 400)

    import re
    import uuid
    base_slug = re.sub(r"[^a-z0-9]+", "-", data["name"].lower()).strip("-")
    slug = base_slug
    
    if query("SELECT id FROM products WHERE slug = %s", (slug,), fetchone=True):
        slug = f"{base_slug}-{str(uuid.uuid4())[:6]}"

    mrp_val = data.get("mrp")
    if mrp_val == "":
        mrp_val = None

    pid = query(
        """INSERT INTO products (name, slug, description, category, price, mrp, stock, unit, is_featured)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (data["name"], slug, data.get("description", ""), data["category"],
         data["price"], mrp_val, data["stock"],
         data.get("unit", "250g"), int(data.get("is_featured", 0))),
        commit=True,
    )
    return success_response("Product created", {"product_id": pid}, 201)


# ── Admin: edit product ─────────────────────────────────────────────────────
@products_bp.route("/admin/products/<int:pid>", methods=["PUT"])
@admin_required
def admin_edit_product(pid):
    data = request.get_json(silent=True) or {}
    allowed = ["name", "description", "category", "price", "mrp", "stock", "unit", "is_featured", "is_active"]
    sets, vals = [], []
    for key in allowed:
        if key in data:
            val = data[key]
            if key == "mrp" and val == "":
                val = None
            sets.append(f"{key} = %s")
            vals.append(val)
    if not sets:
        raise AppError("No fields to update", 400)
    vals.append(pid)
    query(f"UPDATE products SET {', '.join(sets)} WHERE id = %s", tuple(vals), commit=True)
    return success_response("Product updated")


# ── Admin: delete product ───────────────────────────────────────────────────
@products_bp.route("/admin/products/<int:pid>", methods=["DELETE"])
@admin_required
def admin_delete_product(pid):
    query("UPDATE products SET is_active = 0 WHERE id = %s", (pid,), commit=True)
    return success_response("Product deactivated")


# ── Admin: upload product image ─────────────────────────────────────────────
@products_bp.route("/admin/products/<int:pid>/images", methods=["POST"])
@admin_required
def admin_upload_image(pid):
    if "image" not in request.files:
        raise AppError("No image file provided", 400)
    file = request.files["image"]
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        raise AppError("File type not allowed", 400)

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    import uuid
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    is_primary = int(request.form.get("is_primary", 0))
    if is_primary:
        query("UPDATE product_images SET is_primary = 0 WHERE product_id = %s", (pid,), commit=True)

    iid = query(
        "INSERT INTO product_images (product_id, image_url, is_primary) VALUES (%s, %s, %s)",
        (pid, f"/uploads/{filename}", is_primary), commit=True,
    )
    return success_response("Image uploaded", {"image_id": iid, "url": f"/uploads/{filename}"}, 201)


# ── Admin: delete product image ─────────────────────────────────────────────
@products_bp.route("/admin/products/<int:pid>/images/<int:iid>", methods=["DELETE"])
@admin_required
def admin_delete_image(pid, iid):
    img = query("SELECT image_url FROM product_images WHERE id = %s AND product_id = %s", (iid, pid), fetchone=True)
    if not img:
        raise AppError("Image not found", 404)
    query("DELETE FROM product_images WHERE id = %s", (iid,), commit=True)
    # Optional: os.remove(filepath) could be done here if needed.
    return success_response("Image deleted")


# ── Serve uploads ───────────────────────────────────────────────────────────
@products_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)
