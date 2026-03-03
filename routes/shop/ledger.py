# routes/shop/ledger.py
from flask import render_template
from models import Customer, InstallmentProduct
from .helpers import shop_active_or_admin_required, is_active_or_admin


def register(app):
    @app.get("/shop/my/ledger")
    @shop_active_or_admin_required
    def shop_my_ledger(user):
        # إذا مو active ولا admin: اعرض الصفحة بدون بيانات
        if not is_active_or_admin(user):
            return render_template("shop/ledger.html", user=user, customer=None)

        if not user.customer_ref_code:
            return render_template("shop/ledger.html", user=user, customer=None)

        customer = Customer.query.filter_by(custom_id=user.customer_ref_code).first()
        if not customer:
            return render_template("shop/ledger.html", user=user, customer=None)

        cash_debts = customer.cash_debts
        general_payments = customer.general_cash_payments

        # -----------------------------
        # قسم التقسيط (A و B فقط)
        # -----------------------------
        installment_products = []
        installment_details = []

        if customer.ledger != "ديون نقدية":
            installment_products = InstallmentProduct.query.filter_by(customer_id=customer.id).all()

            for product in installment_products:
                total_price = product.total_price or 0
                initial = product.initial_payment or 0
                remaining = total_price - initial

                payments_info = []
                if initial > 0:
                    payments_info.append(
                        {"amount": initial, "date": product.date_added, "remaining": remaining}
                    )

                for p in sorted(product.payments, key=lambda x: x.date_paid):
                    remaining -= (p.amount or 0)
                    payments_info.append(
                        {"amount": p.amount, "date": p.date_paid, "remaining": max(remaining, 0)}
                    )

                # ⚠️ ما منعمل commit داخل GET
                product_is_paid_off = (remaining <= 0)

                installment_details.append(
                    {"product": product, "payments": payments_info, "paid_off": product_is_paid_off}
                )

        # -----------------------------
        # حساب الديون النقدية
        # -----------------------------
        total_cash_debt = sum((debt.price or 0) for debt in cash_debts)
        total_general_paid = sum((p.amount or 0) for p in general_payments)
        remaining_cash = max(total_cash_debt - total_general_paid, 0)

        return render_template(
            "shop/ledger.html",
            user=user,
            customer=customer,
            installment_products=installment_products,
            installment_details=installment_details,
            cash_debts=cash_debts,
            general_payments=general_payments,
            total_cash_debt=total_cash_debt,
            remaining_cash=remaining_cash,
        )
