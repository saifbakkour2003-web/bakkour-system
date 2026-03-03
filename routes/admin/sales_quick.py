from flask import Blueprint, render_template, request, jsonify, current_app
from flask_babel import gettext as _
from datetime import datetime

from extensions import db
from models import Sale, Product
from utils.stock_utils import try_deduct_stock
from utils.admin_auth import admin_required


sales_quick_bp = Blueprint("sales_quick", __name__, url_prefix="/sales")


@sales_quick_bp.route("/quick")
@admin_required
def quick_sale():
    return render_template("sales/quick.html")


@sales_quick_bp.route("/api/product/by-barcode")
@admin_required
def api_product_by_barcode():
    code = (request.args.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "error": "empty_code", "message": _("الكود فارغ")}), 400

    p = Product.query.filter_by(barcode_value=code).first()
    if not p:
        p = Product.query.filter_by(code=code).first()

    if not p:
        return jsonify({"ok": False, "error": "not_found", "message": _("المنتج غير موجود")}), 404

    return jsonify({
        "ok": True,
        "product": {
            "id": p.id,
            "code": p.code,
            "barcode_value": p.barcode_value,
            "name": p.name,
            "price": float(p.base_cash_price or 0),
            "is_available": bool(p.is_available),
            "stock_qty": int(p.stock_qty or 0),
        }
    })


@sales_quick_bp.route("/api/checkout", methods=["POST"])
@admin_required
def api_checkout():
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []

    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "error": "empty_items", "message": _("السلة فارغة")}), 400

    created = 0
    total_amount = 0.0
    total_qty = 0
    now = datetime.utcnow()
    receipt_no = f"Q-{now.strftime('%Y%m%d-%H%M%S')}"

    try:
        normalized = []
        for it in items:
            try:
                pid = int(it.get("product_id"))
                qty = int(it.get("qty", 1))
            except Exception:
                continue

            if pid <= 0 or qty <= 0:
                continue

            try:
                sell_price = float(it.get("sell_price")) if it.get("sell_price") is not None else None
            except Exception:
                sell_price = None

            normalized.append({
                "product_id": pid,
                "qty": qty,
                "sell_price": sell_price
            })

        if not normalized:
            return jsonify({"ok": False, "error": "invalid_items", "message": _("عناصر غير صالحة")}), 400

        products_map = {}

        # ✅ تحقق قبل الكتابة
        for it in normalized:
            p = Product.query.get(it["product_id"])
            if not p:
                return jsonify({
                    "ok": False,
                    "error": "product_not_found",
                    "product_id": it["product_id"],
                    "message": _("منتج غير موجود")
                }), 404

            products_map[p.id] = p

            price = it["sell_price"] if it["sell_price"] is not None else float(p.base_cash_price or 0)
            if price <= 0:
                return jsonify({
                    "ok": False,
                    "error": "invalid_price",
                    "product_id": p.id,
                    "message": _("سعر غير صالح")
                }), 400

            if current_app.config.get("STOCK_DEDUCT_ON_SALE"):
                stock_qty = int(p.stock_qty or 0)
                if stock_qty < it["qty"]:
                    return jsonify({
                        "ok": False,
                        "error": "insufficient_stock",
                        "product_id": p.id,
                        "product_name": p.name,
                        "stock_qty": stock_qty,
                        "requested": it["qty"],
                        "message": _("المخزون غير كافي")
                    }), 409

        # ✅ إنشاء السيلز + خصم المخزون مرة واحدة لكل منتج
        for it in normalized:
            p = products_map[it["product_id"]]

            sell_price = it["sell_price"] if it["sell_price"] is not None else float(p.base_cash_price or 0)
            cost_price = float(p.capital_price or 0)

            total_qty += it["qty"]
            total_amount += float(sell_price) * int(it["qty"])

            for _ in range(it["qty"]):
                sale = Sale(
                    product_id=p.id,
                    customer_id=None,
                    sale_type="cash",
                    sell_price=float(sell_price),
                    cost_price=float(cost_price),
                    date_created=now
                )
                db.session.add(sale)
                created += 1

            if current_app.config.get("STOCK_DEDUCT_ON_SALE"):
                try_deduct_stock(p, it["qty"])

        db.session.commit()
        print(f"[CHECKOUT] receipt={receipt_no} created={created} total={total_amount:.2f}")

        return jsonify({
            "ok": True,
            "created": created,
            "summary": {
                "receipt_no": receipt_no,
                "date_utc": now.isoformat(),
                "total_qty": int(total_qty),
                "total_amount": round(float(total_amount), 2)
            }
        })

    except Exception as e:
        db.session.rollback()
        print("[CHECKOUT ERROR]", e)
        return jsonify({"ok": False, "error": "server_error", "message": _("خطأ بالسيرفر")}), 500