# routes/admin/dashboard.py
from flask import Blueprint, render_template, abort
from flask_babel import gettext as _
from models import Customer, InstallmentProduct, CashDebt
from utils.admin_auth import admin_required

dashboard_bp = Blueprint("dashboard", __name__)

LEDGER_LABELS = {"A": "تقسيط", "B": "R-M", "C": "ديون نقدية"}
LEDGER_DISPLAY = {"A": "دفتر التقسيط", "B": "دفتر R-M", "C": "دفتر الديون النقدية"}


@dashboard_bp.get("/")
@admin_required
def home_dashboard():
    total_customers = Customer.query.count()

    total_installments_remaining = 0.0
    installment_customers = Customer.query.filter(Customer.ledger != "ديون نقدية").all()
    for cus in installment_customers:
        products = InstallmentProduct.query.filter_by(customer_id=cus.id).all()
        for p in products:
            paid = float(p.initial_payment or 0) + sum(float(pay.amount or 0) for pay in p.payments)
            remaining = float(p.total_price or 0) - paid
            total_installments_remaining += max(remaining, 0)

    total_cash_debts_remaining = 0.0
    for cus in Customer.query.all():
        debts = CashDebt.query.filter_by(customer_id=cus.id).all()
        total_debts = sum(float(d.price or 0) for d in debts)
        total_paid = sum(float(p.amount or 0) for p in cus.general_cash_payments)
        total_cash_debts_remaining += max(total_debts - total_paid, 0)

    return render_template(
        "home_dashboard.html",
        total_customers=total_customers,
        total_installments=round(total_installments_remaining, 2),
        total_cash_debts=round(total_cash_debts_remaining, 2),
    )


@dashboard_bp.get("/ledger/<code>")
@admin_required
def ledger_dashboard(code: str):
    if code not in LEDGER_LABELS:
        abort(404)

    ledger_label = LEDGER_LABELS[code]
    ledger_title = LEDGER_DISPLAY[code]

    customers = Customer.query.filter_by(ledger=ledger_label).all()
    customers_count = len(customers)

    total_installments = 0.0
    if code in ("A", "B"):
        for customer in customers:
            products = InstallmentProduct.query.filter_by(customer_id=customer.id).all()
            for p in products:
                paid = float(p.initial_payment or 0) + sum(float(pay.amount or 0) for pay in p.payments)
                remaining = float(p.total_price or 0) - paid
                total_installments += max(remaining, 0)

    total_cash_debts = 0.0
    for customer in customers:
        debts = CashDebt.query.filter_by(customer_id=customer.id).all()
        total_debts = sum(float(d.price or 0) for d in debts)
        total_paid = sum(float(p.amount or 0) for p in customer.general_cash_payments)
        total_cash_debts += max(total_debts - total_paid, 0)

    monthly_profit = 0.0

    return render_template(
        "ledger_dashboard.html",
        ledger_code=code,
        ledger_name=ledger_title,
        customers=customers,
        customers_count=customers_count,
        total_installments=round(total_installments, 2),
        total_cash_debts=round(total_cash_debts, 2),
        monthly_profit=round(monthly_profit, 2),
    )
