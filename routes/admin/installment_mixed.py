# routes/admin/installment_mixed.py
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from extensions import db
from models import Customer, Product, InstallmentProduct, Sale
from utils.stock_utils import try_deduct_stock
from utils.admin_auth import admin_required

installment_mixed_bp = Blueprint("installment_mixed", __name__, url_prefix="/installments")


@installment_mixed_bp.post("/api/add-product")
@admin_required
def add_installment_product_api():
    data = request.get_json(silent=True) or {}

    customer_id = data.get("customer_id")
    product_id = data.get("product_id")
    try:
        qty = int(data.get("qty", 1))
    except Exception:
        qty = 1
    unit_price = data.get("unit_price")

    if not customer_id or not product_id or qty <= 0:
        return jsonify({"ok": False, "error": "bad_request"}), 400

    customer = Customer.query.get(customer_id)
    product = Product.query.get(product_id)
    if not customer or not product:
        return jsonify({"ok": False, "error": "not_found"}), 404

    if unit_price is None:
        unit_price = float(product.base_cash_price or 0)
    else:
        unit_price = float(unit_price)

    total_price = unit_price * qty

    ip = InstallmentProduct(
        customer_id=customer.id,
        name=f"{product.name} x{qty}",
        total_price=total_price,
        initial_payment=0.0,
        monthly_installment=None,
        date_added=datetime.utcnow(),
        paid_off=False
    )
    db.session.add(ip)

    if product.department in ("electrical", "linens"):
        cost_total = float(product.capital_price or 0) * qty
        sale = Sale(
            product_id=product.id,
            customer_id=customer.id,
            sale_type="installment",
            sell_price=total_price,
            cost_price=cost_total,
            date_created=datetime.utcnow()
        )
        db.session.add(sale)

    if current_app.config.get("STOCK_DEDUCT_ON_SALE"):
        try_deduct_stock(product, qty)

    db.session.commit()
    return jsonify({"ok": True, "installment_product_id": ip.id})
