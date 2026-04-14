import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from config import Config
from errors import register_error_handlers
from controller.auth.routes import auth_bp
from controller.products.routes import products_bp
from controller.cart.routes import cart_bp
from controller.orders.routes import orders_bp
from controller.payments.routes import payments_bp
from controller.admin.routes import admin_bp
from controller.profile.routes import profile_bp
from controller.banners.routes import banners_bp, admin_banners_bp


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    import re
    CORS(
        app,
        supports_credentials=True,
        origins=re.compile(r"http://(127\.0\.0\.1|localhost):\d+")
    )

    Bcrypt(app)

    # Register all blueprints
    for bp in [auth_bp, products_bp, cart_bp, orders_bp, payments_bp, admin_bp, profile_bp, banners_bp, admin_banners_bp]:
        app.register_blueprint(bp)

    # Global error handlers
    register_error_handlers(app)

    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)