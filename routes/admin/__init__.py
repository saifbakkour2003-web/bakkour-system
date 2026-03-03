# routes/admin/__init__.py
from .auth import admin_auth_bp
from .users import admin_users_bp
from .brands import admin_brands_bp
from .main_categories import admin_main_categories_bp
from .sub_categories import admin_sub_categories_bp
from .properties import admin_properties_bp

from .client_view import client_bp
from .customers import customers_bp
from .dashboard import dashboard_bp
from .export import export_bp
from .installment_mixed import installment_mixed_bp
from .products import products_bp
from .sales import sales_bp
from .sales_quick import sales_quick_bp
from .installments import installments_bp
from .payments import payments_bp
from .invoices import invoices_bp
from routes.admin.special_offers import admin_special_offers_bp
from .coupons import admin_coupons_bp

def register_admin_routes(app):
    # Auth first
    app.register_blueprint(admin_auth_bp)

    # Core admin
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(client_bp)

    # Tools
    app.register_blueprint(export_bp)
    app.register_blueprint(installment_mixed_bp)

    # Products + Sales
    app.register_blueprint(installments_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(sales_quick_bp)

    # Management (categories, props, brands, users)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(admin_main_categories_bp)
    app.register_blueprint(admin_sub_categories_bp)
    app.register_blueprint(admin_properties_bp)
    app.register_blueprint(admin_brands_bp)

    app.register_blueprint(admin_special_offers_bp)
    app.register_blueprint(admin_coupons_bp)
