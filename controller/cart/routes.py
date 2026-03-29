from flask import Blueprint, request, g
from db import query
from errors import AppError, success_response
from middleware.auth_required import auth_required

cart_bp = Blueprint("cart", __name__, url_prefix="/api/v1/cart")


def _ensure_cart(user_id):
    """Get or create cart for user; returns cart_id."""
    cart = query("SELECT id FROM cart WHERE user_id = %s", (user_id,), fetchone=True)
    if cart:
        return cart["id"]
    return query("INSERT INTO cart (user_id) VALUES (%s)", (user_id,), commit=True)


@cart_bp.route("", methods=["GET"])
@auth_required
def get_cart():
    cart_id = _ensure_cart(g.user_id)
    items = query(
        """SELECT ci.id, ci.quantity,
                  p.id AS product_id, p.name, p.price, p.unit,
                  (SELECT image_url FROM product_images pi
                   WHERE pi.product_id = p.id AND pi.is_primary = 1 LIMIT 1) AS image
           FROM cart_items ci JOIN products p ON p.id = ci.product_id
           WHERE ci.cart_id = %s""",
        (cart_id,),
    )
    total = sum(item["price"] * item["quantity"] for item in items)
    return success_response("Cart fetched", {"items": items, "total": float(total)})


@cart_bp.route("", methods=["POST"])
@auth_required
def add_to_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity   = int(data.get("quantity", 1))
    if not product_id:
        raise AppError("product_id is required", 400)
    if quantity < 1:
        raise AppError("quantity must be >= 1", 400)

    product = query("SELECT id, stock FROM products WHERE id = %s AND is_active = 1", (product_id,), fetchone=True)
    if not product:
        raise AppError("Product not found", 404)
    if product["stock"] < quantity:
        raise AppError("Insufficient stock", 400)

    cart_id = _ensure_cart(g.user_id)
    existing = query(
        "SELECT id, quantity FROM cart_items WHERE cart_id = %s AND product_id = %s",
        (cart_id, product_id), fetchone=True,
    )
    if existing:
        new_qty = existing["quantity"] + quantity
        query("UPDATE cart_items SET quantity = %s WHERE id = %s", (new_qty, existing["id"]), commit=True)
    else:
        query(
            "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (%s, %s, %s)",
            (cart_id, product_id, quantity), commit=True,
        )
    return success_response("Item added to cart", {}, 201)


@cart_bp.route("/<int:item_id>", methods=["PUT"])
@auth_required
def update_cart_item(item_id):
    data = request.get_json(silent=True) or {}
    quantity = int(data.get("quantity", 1))
    if quantity < 1:
        raise AppError("quantity must be >= 1", 400)
    cart_id = _ensure_cart(g.user_id)
    item = query("SELECT id FROM cart_items WHERE id = %s AND cart_id = %s", (item_id, cart_id), fetchone=True)
    if not item:
        raise AppError("Cart item not found", 404)
    query("UPDATE cart_items SET quantity = %s WHERE id = %s", (quantity, item_id), commit=True)
    return success_response("Cart updated")


@cart_bp.route("/<int:item_id>", methods=["DELETE"])
@auth_required
def remove_cart_item(item_id):
    cart_id = _ensure_cart(g.user_id)
    item = query("SELECT id FROM cart_items WHERE id = %s AND cart_id = %s", (item_id, cart_id), fetchone=True)
    if not item:
        raise AppError("Cart item not found", 404)
    query("DELETE FROM cart_items WHERE id = %s", (item_id,), commit=True)
    return success_response("Item removed from cart")


@cart_bp.route("/clear", methods=["DELETE"])
@auth_required
def clear_cart():
    cart_id = _ensure_cart(g.user_id)
    query("DELETE FROM cart_items WHERE cart_id = %s", (cart_id,), commit=True)
    return success_response("Cart cleared")
