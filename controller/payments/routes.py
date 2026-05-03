import hmac
import hashlib
import razorpay
from flask import Blueprint, request, g
from db import query
from errors import AppError, success_response
from middleware.auth_required import auth_required
from config import Config

payments_bp = Blueprint("payments", __name__, url_prefix="/api/v1/payments")


def _razorpay_client():
    return razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))


@payments_bp.route("/create", methods=["POST"])
@auth_required
def create_payment():
    """Create a Razorpay order for a given internal order_id."""
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    if not order_id:
        raise AppError("order_id is required", 400)

    order = query(
        "SELECT id, total_price, status FROM orders WHERE id = %s AND user_id = %s",
        (order_id, g.user_id), fetchone=True,
    )
    if not order:
        raise AppError("Order not found", 404)
    if order["status"] != "pending":
        raise AppError("Order is not in pending state", 400)

    amount_paise = int(float(order["total_price"]) * 100)

    client = _razorpay_client()
    rz_order = client.order.create({
        "amount":   amount_paise,
        "currency": "INR",
        "receipt":  f"inv_{order_id}",
        "payment_capture": 1,
    })

    # Save payment record
    query(
        """INSERT INTO payments (order_id, razorpay_order_id, amount, method)
           VALUES (%s, %s, %s, 'UPI')""",
        (order_id, rz_order["id"], order["total_price"]),
        commit=True,
    )

    return success_response("Payment order created", {
        "razorpay_order_id": rz_order["id"],
        "amount":            amount_paise,
        "currency":          "INR",
        "key_id":            Config.RAZORPAY_KEY_ID,
    })


@payments_bp.route("/verify", methods=["POST"])
@auth_required
def verify_payment():
    """Verify Razorpay payment signature and mark order paid."""
    data = request.get_json(silent=True) or {}
    required = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature"]
    for field in required:
        if not data.get(field):
            raise AppError(f"'{field}' is required", 400)

    # Signature verification
    body = f"{data['razorpay_order_id']}|{data['razorpay_payment_id']}"
    expected = hmac.new(
        Config.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, data["razorpay_signature"]):
        raise AppError("Payment verification failed", 400)

    # Update payment record
    payment = query(
        "SELECT id, order_id FROM payments WHERE razorpay_order_id = %s",
        (data["razorpay_order_id"],), fetchone=True,
    )
    if not payment:
        raise AppError("Payment record not found", 404)

    query(
        """UPDATE payments SET razorpay_payment_id = %s, razorpay_signature = %s, status = 'success'
           WHERE id = %s""",
        (data["razorpay_payment_id"], data["razorpay_signature"], payment["id"]),
        commit=True,
    )
    query(
        "UPDATE orders SET status = 'paid' WHERE id = %s",
        (payment["order_id"],), commit=True,
    )

    return success_response("Payment verified successfully", {"order_id": payment["order_id"]})

@payments_bp.route("/cod", methods=["POST"])
@auth_required
def confirm_cod():
    """Confirm a Cash on Delivery order."""
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    if not order_id:
        raise AppError("order_id is required", 400)

    order = query(
        "SELECT id, total_price, status FROM orders WHERE id = %s AND user_id = %s",
        (order_id, g.user_id), fetchone=True,
    )
    if not order:
        raise AppError("Order not found", 404)
    if order["status"] != "pending":
        raise AppError("Order is not in pending state", 400)

    # Check if a payment record already exists (e.g. they created Razorpay but didn't pay)
    existing_payment = query("SELECT id FROM payments WHERE order_id = %s", (order_id,), fetchone=True)
    if existing_payment:
        query("UPDATE payments SET method = 'COD', status = 'pending' WHERE id = %s", (existing_payment["id"],), commit=True)
    else:
        # Insert payment record with method = 'COD', status = 'pending'
        query(
            """INSERT INTO payments (order_id, razorpay_order_id, amount, method, status)
               VALUES (%s, %s, %s, 'COD', 'pending')""",
            (order_id, f"cod_{order_id}", order["total_price"]),
            commit=True,
        )

    # Update order status to 'processing'
    query(
        "UPDATE orders SET status = 'processing' WHERE id = %s",
        (order_id,), commit=True,
    )

    return success_response("Order confirmed as Cash on Delivery", {"order_id": order_id})
