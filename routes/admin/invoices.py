# routes/admin/invoices.py
from flask import Blueprint, render_template, redirect, url_for
from flask_babel import gettext as _
from datetime import datetime

from models import Customer
from utils.admin_auth import admin_required

invoices_bp = Blueprint("invoices", __name__)


# =========================
# Helpers
# =========================
def _safe_float(x):
    try:
        return float(x or 0)
    except Exception:
        return 0.0


def build_cash_invoice(customer: Customer):
    cash_debts = customer.cash_debts
    general_payments = customer.general_cash_payments

    events = []

    # ديون نقدية (+)
    for debt in cash_debts:
        events.append({
            "type": "cash_debt",
            "name": debt.name,
            "amount": _safe_float(debt.price),
            "date": debt.date_added,
            "sign": "+"
        })

    # دفعات عامة (-)
    for payment in general_payments:
        events.append({
            "type": "general_payment",
            "name": (getattr(payment, "source", None) or _("دفعة عامة")),
            "amount": _safe_float(payment.amount),
            "date": payment.date_paid,
            "sign": "-"
        })

    # ترتيب حسب التاريخ
    events.sort(key=lambda x: x["date"] or datetime.min)

    # رصيد تراكمي
    running_total = 0.0
    for e in events:
        running_total += e["amount"] if e["sign"] == "+" else -e["amount"]
        e["balance"] = round(running_total, 2)

    total_cash_debts = _safe_float(sum((d.price or 0) for d in cash_debts))
    total_general_paid = _safe_float(sum((p.amount or 0) for p in general_payments))

    remaining = total_cash_debts - total_general_paid
    if remaining < 0:
        remaining = 0.0

    return {
        "events": events,
        "total_cash_debts": round(total_cash_debts, 2),
        "total_general_paid": round(total_general_paid, 2),
        "total_paid": round(total_general_paid, 2),
        "remaining": round(remaining, 2),
    }


def build_installments_invoice(customer: Customer):
    installment_products = customer.installment_products

    events = []

    # منتجات تقسيط (+) + دفعات تقسيط (-)
    for ip in installment_products:
        events.append({
            "type": "installment_product",
            "name": ip.name,
            "amount": _safe_float(ip.total_price),
            "date": ip.date_added,
            "sign": "+"
        })

        # دفعة أولى (initial_payment) تعتبر دفعة (-)
        initial = _safe_float(ip.initial_payment)
        if initial > 0:
            events.append({
                "type": "installment_initial_payment",
                "name": _("دفعة أولى"),
                "amount": initial,
                "date": ip.date_added,
                "sign": "-"
            })

        for pay in ip.payments:
            events.append({
                "type": "installment_payment",
                "name": (pay.source or _("دفعة تقسيط")),
                "amount": _safe_float(pay.amount),
                "date": pay.date_paid,
                "sign": "-"
            })

    # ترتيب حسب التاريخ
    events.sort(key=lambda x: x["date"] or datetime.min)

    # رصيد تراكمي
    running_total = 0.0
    for e in events:
        running_total += e["amount"] if e["sign"] == "+" else -e["amount"]
        e["balance"] = round(running_total, 2)

    total_installments = _safe_float(sum((ip.total_price or 0) for ip in installment_products))
    total_initial_paid = _safe_float(sum((ip.initial_payment or 0) for ip in installment_products))
    total_installment_paid = _safe_float(sum((pay.amount or 0) for ip in installment_products for pay in ip.payments))

    total_paid = total_initial_paid + total_installment_paid

    remaining = total_installments - total_paid
    if remaining < 0:
        remaining = 0.0

    return {
        "events": events,
        "total_installments": round(total_installments, 2),
        "total_initial_paid": round(total_initial_paid, 2),
        "total_installment_paid": round(total_installment_paid, 2),
        "total_paid": round(total_paid, 2),
        "remaining": round(remaining, 2),
    }


def build_mixed_invoice(customer: Customer):
    cash = build_cash_invoice(customer)
    inst = build_installments_invoice(customer)

    events = cash["events"] + inst["events"]
    events.sort(key=lambda x: x["date"] or datetime.min)

    running_total = 0.0
    for e in events:
        running_total += e["amount"] if e["sign"] == "+" else -e["amount"]
        e["balance"] = round(running_total, 2)

    total_debts = _safe_float(cash["total_cash_debts"]) + _safe_float(inst["total_installments"])
    total_paid = _safe_float(cash["total_paid"]) + _safe_float(inst["total_paid"])

    remaining = total_debts - total_paid
    if remaining < 0:
        remaining = 0.0

    return {
        "events": events,
        "cash": cash,
        "installments": inst,
        "total_debts": round(total_debts, 2),
        "total_paid": round(total_paid, 2),
        "remaining": round(remaining, 2),
    }


# =========================
# Auto invoice router
# =========================
@invoices_bp.route("/customer/<int:id>/invoice")
@admin_required
def invoice_auto(id):
    customer = Customer.query.get_or_404(id)

    # انت قلت: دفتر التقسيط + RM = مختلط
    # فقط "ديون نقدية" يكون cash-only
    ledger = (customer.ledger or "").strip()

    if ledger in ["ديون نقدية", "ديون", "نقدي", "cash", "cash_debts"]:
        return redirect(url_for("invoices.customer_cash_invoice", id=id))

    # default: mixed
    return redirect(url_for("invoices.customer_mixed_invoice", id=id))


# =========================
# CASH invoice
# =========================
@invoices_bp.route("/customer/<int:id>/invoice/cash")
@admin_required
def customer_cash_invoice(id):
    customer = Customer.query.get_or_404(id)
    data = build_cash_invoice(customer)

    return render_template(
        "invoices/cash_invoice.html",
        customer=customer,
        events=data["events"],
        total_cash_debts=data["total_cash_debts"],
        total_general_paid=data["total_general_paid"],
        total_paid=data["total_paid"],
        remaining=data["remaining"],
        print_mode=False
    )


@invoices_bp.route("/customer/<int:id>/invoice/cash/print")
@admin_required
def print_cash_invoice(id):
    customer = Customer.query.get_or_404(id)
    data = build_cash_invoice(customer)

    return render_template(
        "invoices/cash_invoice.html",
        customer=customer,
        events=data["events"],
        total_cash_debts=data["total_cash_debts"],
        total_general_paid=data["total_general_paid"],
        total_paid=data["total_paid"],
        remaining=data["remaining"],
        print_mode=True
    )


# =========================
# Installments invoice
# =========================
@invoices_bp.route("/customer/<int:id>/invoice/installments")
@admin_required
def customer_installments_invoice(id):
    customer = Customer.query.get_or_404(id)
    data = build_installments_invoice(customer)

    return render_template(
        "invoices/installments_invoice.html",
        customer=customer,
        events=data["events"],
        total_installments=data["total_installments"],
        total_initial_paid=data["total_initial_paid"],
        total_installment_paid=data["total_installment_paid"],
        total_paid=data["total_paid"],
        remaining=data["remaining"],
        print_mode=False
    )


@invoices_bp.route("/customer/<int:id>/invoice/installments/print")
@admin_required
def print_installments_invoice(id):
    customer = Customer.query.get_or_404(id)
    data = build_installments_invoice(customer)

    return render_template(
        "invoices/installments_invoice.html",
        customer=customer,
        events=data["events"],
        total_installments=data["total_installments"],
        total_initial_paid=data["total_initial_paid"],
        total_installment_paid=data["total_installment_paid"],
        total_paid=data["total_paid"],
        remaining=data["remaining"],
        print_mode=True
    )


# =========================
# Mixed invoice
# =========================
@invoices_bp.route("/customer/<int:id>/invoice/mixed")
@admin_required
def customer_mixed_invoice(id):
    customer = Customer.query.get_or_404(id)
    data = build_mixed_invoice(customer)

    return render_template(
        "invoices/mixed_invoice.html",
        customer=customer,
        events=data["events"],
        cash=data["cash"],
        installments=data["installments"],
        total_debts=data["total_debts"],
        total_paid=data["total_paid"],
        remaining=data["remaining"],
        print_mode=False
    )


@invoices_bp.route("/customer/<int:id>/invoice/mixed/print")
@admin_required
def print_mixed_invoice(id):
    customer = Customer.query.get_or_404(id)
    data = build_mixed_invoice(customer)

    return render_template(
        "invoices/mixed_invoice.html",
        customer=customer,
        events=data["events"],
        cash=data["cash"],
        installments=data["installments"],
        total_debts=data["total_debts"],
        total_paid=data["total_paid"],
        remaining=data["remaining"],
        print_mode=True
    )