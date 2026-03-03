# routes/admin/customers.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_babel import gettext as _
from extensions import db
from models import Customer, InstallmentProduct, CashDebt
from utils.admin_auth import admin_required

customers_bp = Blueprint("customers", __name__)

# دفاتر النظام
ledger_codes = {
    "تقسيط": "A",
    "R-M": "B",
    "ديون نقدية": "C",
}
ledger_names = {v: k for k, v in ledger_codes.items()}

from datetime import datetime

def build_cash_ledger_rows(customer):
    """
    يرجّع rows جاهزة للعرض: ديون + دفعات
    مع remaining متسلسل حسب التاريخ.
    """
    rows = []

    for d in (customer.cash_debts or []):
        rows.append({
            "kind": "debt",
            "label": d.name,
            "amount": float(d.price or 0),
            "date": d.date_added,
            "obj": d,
        })

    for p in (customer.general_cash_payments or []):
        rows.append({
            "kind": "payment",
            "label": getattr(p, "source", None) or "دفعة عامة",
            "amount": float(p.amount or 0),
            "date": p.date_paid,
            "obj": p,
        })

    rows.sort(key=lambda x: x["date"] or datetime.min)

    remaining = 0.0
    for r in rows:
        if r["kind"] == "debt":
            remaining += r["amount"]
            r["sign"] = "+"
        else:
            remaining -= r["amount"]
            r["sign"] = "-"
        if remaining < 0:
            remaining = 0.0
        r["remaining"] = round(remaining, 2)

    return rows

@customers_bp.get("/ledger/<code>/customers")
@admin_required
def list_customers(code: str):
    if code not in ledger_names:
        abort(404)

    ledger_label = ledger_names[code]
    customers = Customer.query.filter_by(ledger=ledger_label).all()

    return render_template(
        "customers/index.html",
        ledger_code=code,
        ledger_name=ledger_label,
        customers=customers
    )


@customers_bp.route("/ledger/<code>/customers/add", methods=["GET", "POST"])
@admin_required
def add_customer(code: str):
    if code not in ledger_names:
        abort(404)

    ledger_label = ledger_names[code]

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        phone = (request.form.get("phone") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        if not name:
            flash(_("الاسم مطلوب"), "danger")
            return redirect(request.url)

        count = Customer.query.filter_by(ledger=ledger_label).count()
        custom_id = f"{code}.{count + 1}"

        new_customer = Customer(
            name=name,
            name_tr=name_tr,
            phone=phone,
            notes=notes,
            ledger=ledger_label,
            custom_id=custom_id
        )

        db.session.add(new_customer)
        db.session.commit()

        return redirect(url_for("customers.customer_page", id=new_customer.id))

    return render_template(
        "customers/add.html",
        ledger_code=code,
        ledger_name=ledger_label
    )


@customers_bp.post("/delete_customer/<int:id>")
@admin_required
def delete_customer(id: int):
    customer = Customer.query.get_or_404(id)
    ledger_code = ledger_codes.get(customer.ledger, "A")

    InstallmentProduct.query.filter_by(customer_id=id).delete()
    CashDebt.query.filter_by(customer_id=id).delete()

    db.session.delete(customer)
    db.session.commit()

    flash(_("تم حذف الزبون"), "success")
    return redirect(url_for("customers.list_customers", code=ledger_code))


@customers_bp.route("/edit_customer/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_customer(id: int):
    customer = Customer.query.get_or_404(id)

    if request.method == "POST":
        customer.name = request.form.get("name", customer.name)
        customer.name_tr = (request.form.get("name_tr") or "").strip() or None
        customer.phone = request.form.get("phone", customer.phone)
        customer.notes = request.form.get("notes", customer.notes)

        new_ledger = (request.form.get("ledger") or customer.ledger).strip()
        if new_ledger in ledger_codes:  # إذا الفورم يرسل عربي
            customer.ledger = new_ledger
        elif new_ledger in ledger_names.values():  # احتياط
            customer.ledger = new_ledger

        db.session.commit()
        flash(_("تم تعديل بيانات الزبون ✅"), "success")
        return redirect(url_for("customers.customer_page", id=customer.id))

    return render_template("customers/edit.html", customer=customer)


@customers_bp.get("/customer/<int:id>")
@admin_required
def customer_page(id: int):
    customer = Customer.query.get_or_404(id)

    cash_debts = customer.cash_debts
    general_payments = customer.general_cash_payments

    installment_products = []
    installment_details = []

    if customer.ledger != "ديون نقدية":
        installment_products = InstallmentProduct.query.filter_by(customer_id=id).all()

        for product in installment_products:
            total_price = float(product.total_price or 0)
            initial = float(product.initial_payment or 0)
            remaining = total_price - initial

            payments_info = []
            if initial > 0:
                payments_info.append({"amount": initial, "date": product.date_added, "remaining": remaining})

            for p in sorted(product.payments, key=lambda x: x.date_paid):
                remaining -= float(p.amount or 0)
                payments_info.append({"amount": p.amount, "date": p.date_paid, "remaining": max(remaining, 0)})

            product.paid_off = (remaining <= 0)

            installment_details.append({"product": product, "payments": payments_info})

    db.session.commit()

    total_cash_debt = float(sum((d.price or 0) for d in cash_debts))
    total_general_paid = float(sum((p.amount or 0) for p in general_payments))
    remaining_cash = max(total_cash_debt - total_general_paid, 0)
    cash_rows = build_cash_ledger_rows(customer)
    cash_remaining = cash_rows[-1]["remaining"] if cash_rows else 0.0
    
    return render_template(
        "customers/view.html",
        customer=customer,
        ledger_code=ledger_codes,
        installment_products=installment_products,
        installment_details=installment_details,
        cash_debts=cash_debts,
        general_payments=general_payments,
        total_cash_debt=round(total_cash_debt, 2),
        remaining_cash=round(remaining_cash, 2),
        cash_rows=cash_rows,
        cash_remaining=cash_remaining,
    )
