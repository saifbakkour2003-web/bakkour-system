# routes/admin/client_view.py
from flask import Blueprint, render_template
from models import Customer
from utils.admin_auth import admin_required

client_bp = Blueprint("client", __name__)  # keep same paths


@client_bp.get("/client/<int:id>")
@admin_required
def client_view(id: int):
    customer = Customer.query.get_or_404(id)
    return render_template("client/client_view.html", customer=customer)


@client_bp.get("/client/<int:id>/cash_details")
@admin_required
def cash_details(id: int):
    customer = Customer.query.get_or_404(id)
    cash_debts = customer.cash_debts
    return render_template(
        "client/cash_details.html",
        customer=customer,
        cash_debts=cash_debts
    )


@client_bp.get("/client/<int:id>/installment_details")
@admin_required
def installment_details(id: int):
    customer = Customer.query.get_or_404(id)
    installment_products = customer.installment_products
    return render_template(
        "client/installment_details.html",
        customer=customer,
        installment_products=installment_products
    )
