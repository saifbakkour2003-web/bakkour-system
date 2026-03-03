import os
from flask import Flask
from flask_migrate import Migrate
import config

from extensions import db
from i18n import init_i18n
from utils.db_schema import apply_all_patches, ensure_sqlite_column

# =========================
# App Setup
# =========================

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))




app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# فعل Secure فقط لما تكون Production
if not app.debug:
    app.config["SESSION_COOKIE_SECURE"] = True

# =========================
# Database (PostgreSQL)
# =========================

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:Seyfo2101%40@127.0.0.1:5432/bakkour"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# =========================
# Stock behavior
# =========================

app.config["STOCK_DEDUCT_ON_SALE"] = True
app.config["STOCK_BLOCK_IF_INSUFFICIENT"] = False

# Load other config values
app.config.from_object("config")

# =========================
# Upload config
# =========================

UPLOAD_FOLDER_PRODUCTS = os.path.join("static", "uploads", "products")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER_PRODUCTS"] = UPLOAD_FOLDER_PRODUCTS
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ALLOWED_IMAGE_EXTENSIONS

# =========================
# Contact config
# =========================

app.config["CONTACT_PHONE_DISPLAY"] = config.CONTACT_PHONE_DISPLAY
app.config["WHATSAPP_PHONE_E164"] = config.WHATSAPP_PHONE_E164
app.config["SHAM_CASH_WALLET"] = "e7e80d54bb624e5fe88f3346b62753ca"


@app.context_processor
def inject_contact_info():
    phone = app.config.get("CONTACT_PHONE_DISPLAY", "")
    wa = app.config.get("WHATSAPP_PHONE_E164", "")
    wa_link = f"https://wa.me/{wa}" if wa else ""
    return {
        "CONTACT_PHONE_DISPLAY": phone,
        "WHATSAPP_LINK": wa_link,
    }


# =========================
# Extensions
# =========================

db.init_app(app)
init_i18n(app)

# i18n blueprint (مهم جداً)
from routes.i18n import i18n_bp
app.register_blueprint(i18n_bp)

# context processors
from context_processors import inject_i18n, inject_storefront_user

app.context_processor(inject_i18n)
app.context_processor(inject_storefront_user)

migrate = Migrate(app, db)

# =========================
# Import Models (for migrations)
# =========================

from models import *  # noqa


# =========================
# Register Routes
# =========================

# Shop
from routes.shop import register_shop_routes
register_shop_routes(app)

# Admin
from routes.admin import register_admin_routes
register_admin_routes(app)


# =========================
# SQLite-only patches (legacy)
# =========================

def is_sqlite():
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    return uri.startswith("sqlite")


def apply_db_patches():
    ensure_sqlite_column(
        table_name="general_cash_payment",
        column_name="source",
        column_sql="TEXT DEFAULT 'دفعة عامة'",
    )


with app.app_context():
    if is_sqlite():
        apply_db_patches()


# =========================
# Run App
# =========================

if __name__ == "__main__":
    with app.app_context():
        apply_all_patches()
    app.run()