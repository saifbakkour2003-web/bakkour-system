# routes/admin/payments.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_babel import gettext as _
from datetime import datetime

from extensions import db
from models import (
    Customer,
    CashDebt,
    GeneralCashPayment,
    Product,
    Sale,
)
from utils.stock_utils import try_deduct_stock
from utils.admin_auth import admin_required

payments_bp = Blueprint("payments", __name__)

# =====================================================
# إضافة دين نقدي
# =====================================================
@payments_bp.route("/customer/<int:id>/add_cash_debt", methods=["GET", "POST"])
@admin_required
def add_cash_debt(id):
    customer = Customer.query.get_or_404(id)

    if request.method == "POST":
        mode = (request.form.get("mode") or "product").strip()  # product / manual

        # التاريخ
        date_str = request.form.get("date_added")
        try:
            date_added = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.utcnow()
        except ValueError:
            date_added = datetime.utcnow()

        if mode == "manual":
            # ✅ دين يدوي بدون منتج
            name = (request.form.get("manual_name") or "").strip()
            if not name:
                flash(_("اسم الدين مطلوب"), "danger")
                return redirect(request.url)

            try:
                price = float(request.form.get("price", 0) or 0)
                capital = float(request.form.get("capital_price", 0) or 0)
                if price <= 0 or capital < 0:
                    raise ValueError
            except ValueError:
                flash(_("السعر/رأس المال غير صالح"), "danger")
                return redirect(request.url)

            debt = CashDebt(
                customer_id=customer.id,
                product_id=None,
                name=name,
                price=price,
                date_added=date_added
            )
            db.session.add(debt)

            # ✅ Sale لتقرير الأرباح
            sale = Sale(
                product_id=None,
                customer_id=customer.id,
                sale_type="debt_manual",
                sell_price=price,
                cost_price=capital,
                manual_name=name,
                manual_code=(request.form.get("manual_code") or "").strip() or None,
                date_created=datetime.utcnow()
            )
            db.session.add(sale)

            db.session.commit()
            flash(_("تم إضافة الدين اليدوي بنجاح ✅"), "success")
            return redirect(url_for("customers.customer_page", id=customer.id))

        # ==========================
        # وضع المنتج المسجل (قديمك)
        # ==========================
        product_code = (request.form.get("product_code") or "").strip()

        product = Product.query.filter_by(code=product_code).first()
        if not product:
            flash(_("كود المنتج غير صحيح ❌"), "danger")
            return render_template(
                "payments/add_cash_debt.html",
                customer=customer,
                product_name=None,
                datetime=datetime
            )

        try:
            price = float(request.form.get("price", 0) or 0)
            if price <= 0:
                raise ValueError
        except ValueError:
            flash(_("السعر غير صالح"), "danger")
            return render_template(
                "payments/add_cash_debt.html",
                customer=customer,
                product_name=product.name,
                datetime=datetime
            )

        debt = CashDebt(
            customer_id=customer.id,
            product_id=product.id,
            name=product.name,
            price=price,
            date_added=date_added
        )
        db.session.add(debt)

        sale = Sale(
            product_id=product.id,
            customer_id=customer.id,
            sale_type="debt",
            sell_price=price,
            cost_price=product.capital_price,
            date_created=datetime.utcnow()
        )
        db.session.add(sale)

        if current_app.config.get("STOCK_DEDUCT_ON_SALE"):
            try_deduct_stock(product, 1)

        db.session.commit()

        flash(_("تم إضافة الدين النقدي بنجاح ✅"), "success")
        return redirect(url_for("customers.customer_page", id=customer.id))

    return render_template(
        "payments/add_cash_debt.html",
        customer=customer,
        product_name=None,
        datetime=datetime
    )


# =====================================================
# حذف دين نقدي
# =====================================================
@payments_bp.route("/cash_debt/<int:id>/delete", methods=["POST"])
@admin_required
def delete_cash_debt(id):
    debt = CashDebt.query.get_or_404(id)
    customer_id = debt.customer_id

    db.session.delete(debt)
    db.session.commit()

    flash(_("تم حذف الدين النقدي 🗑️"), "success")
    return redirect(url_for("customers.customer_page", id=customer_id))


# =====================================================
# تعديل دين نقدي
# =====================================================
@payments_bp.route("/cash_debt/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_cash_debt(id):
    debt = CashDebt.query.get_or_404(id)

    if request.method == "POST":
        debt.name = request.form.get("name", debt.name)

        try:
            debt.price = float(request.form.get("price", debt.price))
        except ValueError:
            flash(_("السعر غير صالح"), "danger")
            return redirect(request.url)

        date_str = request.form.get("date_added")
        if date_str:
            try:
                debt.date_added = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass

        db.session.commit()
        flash(_("تم تعديل الدين النقدي بنجاح ✅"), "success")

        return redirect(url_for("customers.customer_page", id=debt.customer_id))

    return render_template("payments/edit_cash_debt.html", debt=debt)


# =====================================================
# إضافة دفعة عامة (تغطي كل الديون النقدية)
# =====================================================
@payments_bp.route("/customer/<int:id>/add_general_cash_payment", methods=["GET", "POST"])
@admin_required
def add_general_cash_payment(id):
    customer = Customer.query.get_or_404(id)

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0) or 0)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash(_("المبلغ غير صالح ❌"), "danger")
            return redirect(url_for("customers.customer_page", id=id))

        # ✅ NEW: source (اختياري)
        source = (request.form.get("source") or "").strip() or "دفعة عامة"

        date_paid_str = request.form.get("date_paid")
        try:
            date_paid = (
                datetime.strptime(date_paid_str, "%Y-%m-%d")
                if date_paid_str else datetime.utcnow()
            )
        except ValueError:
            date_paid = datetime.utcnow()

        payment = GeneralCashPayment(
            customer_id=id,
            amount=amount,
            date_paid=date_paid,
            source=source,  # ✅ NEW
        )

        db.session.add(payment)
        db.session.commit()

        flash(_("تمت إضافة الدفعة العامة بنجاح ✅"), "success")
        return redirect(url_for("customers.customer_page", id=id))

    return render_template(
        "payments/add_general_payment.html",
        customer=customer,
        datetime=datetime
    )


# =====================================================
# حذف دفعة عامة
# =====================================================
@payments_bp.route("/general_payment/<int:id>/delete", methods=["POST"])
@admin_required
def delete_general_payment(id):
    payment = GeneralCashPayment.query.get_or_404(id)
    customer_id = payment.customer_id

    db.session.delete(payment)
    db.session.commit()

    flash(_("تم حذف الدفعة العامة 🗑️"), "success")
    return redirect(url_for("customers.customer_page", id=customer_id))


# =====================================================
# تعديل دفعة عامة
# =====================================================
@payments_bp.route("/general_payment/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_general_payment(id):
    payment = GeneralCashPayment.query.get_or_404(id)
    customer = payment.customer

    if request.method == "POST":
        try:
            payment.amount = float(request.form.get("amount", payment.amount))
        except ValueError:
            flash(_("المبلغ غير صالح ❌"), "danger")
            return redirect(request.url)

        # ✅ NEW: source editable (اختياري)
        payment.source = (request.form.get("source") or "").strip() or (payment.source or "دفعة عامة")

        date_str = request.form.get("date_paid")
        if date_str:
            try:
                payment.date_paid = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass

        db.session.commit()
        flash(_("تم تعديل الدفعة العامة بنجاح ✅"), "success")

        return redirect(url_for("customers.customer_page", id=customer.id))

    return render_template(
        "payments/edit_general_payment.html",
        payment=payment,
        customer=customer
    )