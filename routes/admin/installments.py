# routes/admin/installments.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_babel import gettext as _
from datetime import datetime
from collections import Counter

from extensions import db
from models import (
    Customer,
    InstallmentProduct,
    InstallmentPayment,
    InstallmentItem,
    Product,
    Sale,
)
from utils.stock_utils import try_deduct_stock
from utils.admin_auth import admin_required


installments_bp = Blueprint("installments", __name__)

# ======================
# إضافة منتج تقسيط
# ======================
@installments_bp.route("/customer/<int:id>/add_installment_product", methods=["GET", "POST"])
@admin_required
def add_installment_product(id):
    customer = Customer.query.get_or_404(id)

    if request.method == "POST":
        # ====== core fields ======
        try:
            total_price = float(request.form.get("total_price") or 0)
            initial_payment = float(request.form.get("initial_payment") or 0)
            monthly_installment = float(request.form.get("monthly_installment") or 0)
            if total_price <= 0 or initial_payment < 0 or monthly_installment < 0:
                raise ValueError
        except ValueError:
            flash(_("الرجاء إدخال قيم صحيحة"), "danger")
            return redirect(request.url)

        # ====== date ======
        date_str = request.form.get("date_added")
        try:
            date_added = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.utcnow()
        except ValueError:
            date_added = datetime.utcnow()

        # ====== product codes ======
        codes = request.form.getlist("product_code[]")
        codes = [c.strip() for c in codes if (c or "").strip()]
        if not codes:
            flash(_("أدخل كود منتج واحد على الأقل"), "danger")
            return redirect(request.url)

        products = []
        bad_codes = []
        for code in codes:
            p = Product.query.filter_by(code=code).first()
            if not p:
                bad_codes.append(code)
            else:
                products.append(p)

        if bad_codes:
            flash(_("أكواد غير صحيحة: ") + ", ".join(bad_codes), "danger")
            return redirect(request.url)

        # ====== contract name ======
        contract_name = " + ".join([p.name for p in products])

        contract = InstallmentProduct(
            customer_id=customer.id,
            name=contract_name,
            total_price=total_price,
            initial_payment=initial_payment,
            monthly_installment=monthly_installment,
            date_added=date_added,
            paid_off=False
        )
        db.session.add(contract)
        db.session.flush()  # to get contract.id

        # ====== qty per product ======
        counter = Counter([p.id for p in products])
        unique_products = {p.id: p for p in products}

        # ====== create InstallmentItem rows + stock ======
        for pid, qty in counter.items():
            p = unique_products[pid]
            db.session.add(InstallmentItem(
                installment_product_id=contract.id,
                product_id=p.id,
                name=p.name,
                qty=int(qty),
            ))

            if current_app.config.get("STOCK_DEDUCT_ON_SALE"):
                try_deduct_stock(p, int(qty))

        # ====== register sales for profits ======
        # We'll create sales rows for each unique product, and allocate total_price proportionally
        # based on base_cash_price (fallback 1). Revenue sum == total_price.
        weights = {}
        total_weight = 0.0
        for pid, qty in counter.items():
            p = unique_products[pid]
            w = float(p.base_cash_price or 0)
            if w <= 0:
                w = 1.0
            w = w * float(qty)
            weights[pid] = w
            total_weight += w

        sale_type_marker = "installment"
        allocated_sum = 0.0
        pid_list = list(counter.keys())

        for idx, pid in enumerate(pid_list):
            p = unique_products[pid]
            qty = int(counter[pid])

            # allocate revenue
            if total_weight > 0:
                portion = (total_price * (weights[pid] / total_weight))
            else:
                portion = total_price / max(len(pid_list), 1)

            portion = round(float(portion), 2)

            # last row fix rounding so sum == total_price
            if idx == len(pid_list) - 1:
                portion = round(float(total_price) - float(allocated_sum), 2)

            allocated_sum += portion

            cost_total = round(float(p.capital_price or 0) * qty, 2)

            db.session.add(Sale(
                product_id=p.id,
                customer_id=customer.id,
                sale_type=sale_type_marker,
                sell_price=portion,
                cost_price=cost_total,
                date_created=date_added
            ))

        db.session.commit()
        flash(_("تمت إضافة التقسيط بنجاح ✅"), "success")
        return redirect(url_for("customers.customer_page", id=customer.id))

    return render_template("installments/add.html", customer=customer, datetime=datetime)


# ======================
# حذف منتج تقسيط
# ======================
@installments_bp.route("/installment_product/<int:id>/delete", methods=["POST"])
@admin_required
def delete_installment_product(id):
    product = InstallmentProduct.query.get_or_404(id)
    customer = product.customer

    if customer and customer.ledger == "ديون نقدية":
        flash(_("هذا الدفتر لا يحتوي على أقساط"), "danger")
        return redirect(url_for("customers.customer_page", id=customer.id))

    cid = product.customer_id
    db.session.delete(product)
    db.session.commit()

    flash(_("تم حذف منتج التقسيط 🗑️"), "success")
    return redirect(url_for("customers.customer_page", id=cid))


# ======================
# إضافة دفعة قسط
# ======================
@installments_bp.route("/installment_product/<int:id>/add_payment", methods=["GET", "POST"])
@admin_required
def add_installment_payment(id):
    product = InstallmentProduct.query.get_or_404(id)
    customer = product.customer

    if customer and customer.ledger == "ديون نقدية":
        flash(_("هذا الدفتر لا يحتوي على أقساط"), "danger")
        return redirect(url_for("customers.customer_page", id=customer.id))

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            source = request.form.get("source", _("دفعة على المنتج"))

            date_paid_str = request.form.get("date_paid")
            date_paid = datetime.fromisoformat(date_paid_str) if date_paid_str else datetime.utcnow()

        except (KeyError, ValueError):
            flash(_("بيانات غير صحيحة في الفورم"), "danger")
            return redirect(request.url)

        payment = InstallmentPayment(
            product_id=id,
            amount=amount,
            source=source,
            date_paid=date_paid
        )
        db.session.add(payment)

        total_paid = sum(float(p.amount or 0) for p in product.payments) + float(amount or 0)
        remaining = float(product.total_price or 0) - float(product.initial_payment or 0) - total_paid
        product.paid_off = (remaining <= 0)

        db.session.commit()
        flash(_("تمت إضافة الدفعة ✅"), "success")
        return redirect(url_for("customers.customer_page", id=product.customer_id))

    return render_template("installments/add_payment.html", product=product)


# ======================
# حذف دفعة قسط
# ======================
@installments_bp.route("/installment_payment/<int:id>/delete", methods=["POST"])
@admin_required
def delete_installment_payment(id):
    payment = InstallmentPayment.query.get_or_404(id)
    customer = payment.product.customer if payment.product else None

    if customer and customer.ledger == "ديون نقدية":
        flash(_("هذا الدفتر لا يحتوي على أقساط"), "danger")
        return redirect(url_for("customers.customer_page", id=customer.id))

    cid = payment.product.customer_id
    db.session.delete(payment)
    db.session.commit()

    flash(_("تم حذف الدفعة 🗑️"), "success")
    return redirect(url_for("customers.customer_page", id=cid))


# routes/admin/installments.py
# ======================
# عرض فواتير التقسيط الغير مسددة
# ======================
@installments_bp.route("/customer/<int:id>/installments_invoice")
@admin_required
def installments_invoice(id):
    customer = Customer.query.get_or_404(id)

    installment_products = [p for p in customer.installment_products if not p.paid_off]

    if not installment_products:
        flash(_("لا يوجد منتجات تقسيط غير مسددة لهذا الزبون."), "info")
        return redirect(url_for("customers.customer_page", id=id))

    return render_template(
        "installments/invoice_list.html",
        customer=customer,
        products=installment_products
    )


# ======================
# فاتورة إغلاق منتج تقسيط
# ======================
@installments_bp.route("/installment_product/<int:id>/close_invoice")
@admin_required
def close_installment_invoice(id):
    product = InstallmentProduct.query.get_or_404(id)
    customer = product.customer

    total_price = float(product.total_price or 0)
    initial = float(product.initial_payment or 0)
    remaining = total_price - initial

    payments_info = []

    if initial > 0:
        payments_info.append({
            "amount": initial,
            "date": product.date_added,
            "remaining": remaining,
            "is_initial": True
        })

    for p in sorted(product.payments, key=lambda x: x.date_paid):
        remaining -= float(p.amount or 0)
        payments_info.append({
            "amount": p.amount,
            "date": p.date_paid,
            "remaining": remaining if remaining > 0 else 0,
            "is_initial": False
        })

    return render_template(
        "installments/close_invoice.html",
        product=product,
        customer=customer,
        payments=payments_info
    )
