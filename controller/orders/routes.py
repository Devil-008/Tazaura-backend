from flask import Blueprint, request, g
from db import query, get_db
from errors import AppError, success_response
from middleware.auth_required import auth_required
from middleware.admin_required import admin_required

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


@orders_bp.route("", methods=["POST"])
@auth_required
def create_order():
    """Create order from cart; reduces stock."""
    data = request.get_json(silent=True) or {}
    address_id = data.get("address_id")

    # Get cart items
    cart = query("SELECT id FROM cart WHERE user_id = %s", (g.user_id,), fetchone=True)
    if not cart:
        raise AppError("Cart is empty", 400)

    items = query(
        """SELECT ci.product_id, ci.quantity, p.price, p.stock, p.name
           FROM cart_items ci JOIN products p ON p.id = ci.product_id
           WHERE ci.cart_id = %s""",
        (cart["id"],),
    )
    if not items:
        raise AppError("Cart is empty", 400)

    # Validate stock
    for item in items:
        if item["stock"] < item["quantity"]:
            raise AppError(f"Insufficient stock for {item['name']}", 400)

    total = sum(item["price"] * item["quantity"] for item in items)

    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO orders (user_id, address_id, total_price) VALUES (%s, %s, %s)",
            (g.user_id, address_id, total),
        )
        order_id = cursor.lastrowid

        for item in items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                (order_id, item["product_id"], item["quantity"], item["price"]),
            )
            cursor.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (item["quantity"], item["product_id"]),
            )

        # Clear cart
        cursor.execute("DELETE FROM cart_items WHERE cart_id = %s", (cart["id"],))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return success_response("Order placed successfully", {"order_id": order_id, "total": float(total)}, 201)


@orders_bp.route("", methods=["GET"])
@auth_required
def list_orders():
    orders = query(
        """SELECT o.id, o.total_price, o.status, o.created_at,
                  COUNT(oi.id) AS item_count
           FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id
           WHERE o.user_id = %s
           GROUP BY o.id ORDER BY o.created_at DESC""",
        (g.user_id,),
    )
    return success_response("Orders fetched", orders)


@orders_bp.route("/<int:order_id>", methods=["GET"])
@auth_required
def get_order(order_id):
    order = query(
        "SELECT * FROM orders WHERE id = %s AND user_id = %s",
        (order_id, g.user_id), fetchone=True,
    )
    if not order:
        raise AppError("Order not found", 404)

    items = query(
        """SELECT oi.quantity, oi.unit_price, p.name, p.unit,
                  (SELECT image_url FROM product_images pi WHERE pi.product_id = p.id AND pi.is_primary = 1 LIMIT 1) AS image
           FROM order_items oi JOIN products p ON p.id = oi.product_id
           WHERE oi.order_id = %s""",
        (order_id,),
    )
    payment = query(
        "SELECT method, status, razorpay_payment_id FROM payments WHERE order_id = %s",
        (order_id,), fetchone=True,
    )
    order["items"]   = items
    order["payment"] = payment
    return success_response("Order fetched", order)
