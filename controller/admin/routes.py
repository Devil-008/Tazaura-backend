from flask import Blueprint, request, g, send_file
from io import BytesIO
from db import query
from errors import success_response, AppError
from middleware.admin_required import admin_required
from helper.invoice import generate_invoice_pdf

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():
    total_users  = query("SELECT COUNT(*) AS cnt FROM users WHERE role='user'", fetchone=True)["cnt"]
    total_orders = query("SELECT COUNT(*) AS cnt FROM orders", fetchone=True)["cnt"]
    revenue      = query("SELECT IFNULL(SUM(total_price),0) AS rev FROM orders WHERE status='paid'", fetchone=True)["rev"]
    total_products = query("SELECT COUNT(*) AS cnt FROM products WHERE is_active=1", fetchone=True)["cnt"]
    recent_orders = query(
        """SELECT o.id, o.total_price, o.status, o.created_at, u.name AS customer
           FROM orders o JOIN users u ON u.id = o.user_id
           ORDER BY o.created_at DESC LIMIT 5"""
    )
    return success_response("Dashboard data", {
        "total_users":    total_users,
        "total_orders":   total_orders,
        "total_revenue":  float(revenue),
        "total_products": total_products,
        "recent_orders":  recent_orders,
    })


@admin_bp.route("/orders", methods=["GET"])
@admin_required
def list_all_orders():
    status = request.args.get("status", "")
    page   = max(1, int(request.args.get("page", 1)))
    limit  = 20
    offset = (page - 1) * limit

    where  = "WHERE o.status = %s" if status else ""
    params = (status, limit, offset) if status else (limit, offset)

    orders = query(
        f"""SELECT o.id, o.total_price, o.status, o.created_at, u.name AS customer, u.email
            FROM orders o JOIN users u ON u.id = o.user_id
            {where} ORDER BY o.created_at DESC LIMIT %s OFFSET %s""",
        params,
    )
    return success_response("Orders fetched", orders)


@admin_bp.route("/orders/<int:order_id>", methods=["PATCH"])
@admin_required
def update_order_status(order_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    allowed = ["pending", "paid", "processing", "shipped", "delivered", "cancelled"]
    if status not in allowed:
        raise AppError(f"Status must be one of {allowed}", 400)
    query("UPDATE orders SET status = %s WHERE id = %s", (status, order_id), commit=True)
    return success_response("Order status updated")


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    page   = max(1, int(request.args.get("page", 1)))
    limit  = 20
    offset = (page - 1) * limit
    users = query(
        "SELECT id, name, username, email, role, is_active, created_at FROM users LIMIT %s OFFSET %s",
        (limit, offset),
    )
    return success_response("Users fetched", users)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["PATCH"])
@admin_required
def toggle_user(user_id):
    user = query("SELECT is_active FROM users WHERE id = %s", (user_id,), fetchone=True)
    if not user:
        raise AppError("User not found", 404)
    new_status = 0 if user["is_active"] else 1
    query("UPDATE users SET is_active = %s WHERE id = %s", (new_status, user_id), commit=True)
    return success_response("User status toggled", {"is_active": bool(new_status)})


@admin_bp.route("/orders/<int:order_id>", methods=["GET"])
@admin_required
def get_order_details(order_id):
    order = query(
        """SELECT o.*, u.name AS customer_name, u.email AS customer_email,
                  a.full_name AS bill_to_name, a.phone AS bill_to_phone, 
                  a.line1, a.line2, a.city, a.state, a.pincode
           FROM orders o 
           JOIN users u ON u.id = o.user_id
           LEFT JOIN addresses a ON a.id = o.address_id
           WHERE o.id = %s""",
        (order_id,), fetchone=True,
    )
    if not order:
        raise AppError("Order not found", 404)

    items = query(
        """SELECT oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS amount, 
                  p.name, p.unit
           FROM order_items oi 
           JOIN products p ON p.id = oi.product_id
           WHERE oi.order_id = %s""",
        (order_id,),
    )
    payment = query(
        "SELECT method, status, razorpay_payment_id, created_at FROM payments WHERE order_id = %s",
        (order_id,), fetchone=True,
    )
    order["items"] = items
    order["payment"] = payment
    return success_response("Order details fetched", order)


@admin_bp.route("/orders/<int:order_id>/invoice", methods=["GET"])
@admin_required
def download_invoice(order_id):
    order = query(
        """SELECT o.*, u.name AS customer_name, u.email AS customer_email,
                  a.full_name AS bill_to_name, a.phone AS bill_to_phone, 
                  a.line1, a.line2, a.city, a.state, a.pincode
           FROM orders o 
           JOIN users u ON u.id = o.user_id
           LEFT JOIN addresses a ON a.id = o.address_id
           WHERE o.id = %s""",
        (order_id,), fetchone=True,
    )
    if not order:
        raise AppError("Order not found", 404)

    items = query(
        """SELECT oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS amount, 
                  p.name, p.unit
           FROM order_items oi 
           JOIN products p ON p.id = oi.product_id
           WHERE oi.order_id = %s""",
        (order_id,),
    )
    payment = query(
        "SELECT method, status, razorpay_payment_id, created_at FROM payments WHERE order_id = %s",
        (order_id,), fetchone=True,
    )
    
    pdf_data = generate_invoice_pdf(order, items, payment)
    return send_file(
        BytesIO(pdf_data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"invoice_{order_id}.pdf"
    )
