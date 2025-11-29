from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = "saif"  # ممكن أي قيمة طويلة ومعقدة
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://bakkour_system_db_user:71Ahw6kVaDekMK51pPi9m6RSZ08wYq4x@dpg-d4llva9r0fns73fdlt4g-a.frankfurt-postgres.render.com/bakkour_system_db"
app.config['SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ===========================
# Models
# ===========================

from datetime import datetime
# from app import db

class Customer(db.Model):
    __tablename__ = 'customer'
    __table_args__ = {'extend_existing': True}  # هالسطرة

    id = db.Column(db.Integer, primary_key=True)
    custom_id = db.Column(db.String(20), unique=True)  # ← ← هنا ضفناه

    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), default='')
    notes = db.Column(db.Text, default='')
    ledger = db.Column(db.String(50), default='تقسيط')

    # العلاقات القديمة موجودة
    installment_products = db.relationship(
        'InstallmentProduct',
        back_populates='customer',
        cascade='all, delete-orphan',
        lazy='dynamic'  # أضفنا lazy
    )
    cash_debts = db.relationship(
        'CashDebt',
        back_populates='customer',
        cascade='all, delete-orphan',
        # lazy='select'  # أضفنا lazy
    )
    general_cash_payments = db.relationship(
        "GeneralCashPayment",
        back_populates="customer",
        cascade="all, delete-orphan",
        # lazy="select"
    )


class InstallmentProduct(db.Model):
    __tablename__ = 'installment_product'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    initial_payment = db.Column(db.Float, nullable=False, default=0.0)
    monthly_installment = db.Column(db.Float, nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    paid_off = db.Column(db.Boolean, default=False)

    # العلاقة القديمة موجودة
    customer = db.relationship('Customer', back_populates='installment_products')
    payments = db.relationship(
        'InstallmentPayment',
        back_populates='product',
        cascade='all, delete-orphan'
    )


class InstallmentPayment(db.Model):
    __tablename__ = 'installment_payment'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('installment_product.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(100), default="دفعة على المنتج")

    product = db.relationship('InstallmentProduct', back_populates='payments')


class CashDebt(db.Model):
    __tablename__ = 'cash_debt'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    paid_off = db.Column(db.Boolean, default=False)

    customer = db.relationship('Customer', back_populates='cash_debts')
    payments = db.relationship('CashDebtPayment', back_populates='debt', cascade='all, delete-orphan')


class CashDebtPayment(db.Model):
    __tablename__ = 'cash_debt_payment'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    cash_debt_id = db.Column(db.Integer, db.ForeignKey('cash_debt.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.DateTime, default=datetime.utcnow)

    debt = db.relationship('CashDebt', back_populates='payments')

class GeneralCashPayment(db.Model):
    __tablename__ = 'general_cash_payment'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.DateTime, default=datetime.utcnow)

    # customer = db.relationship('Customer', backref='general_payments')
    customer = db.relationship("Customer", back_populates="general_cash_payments")


# ===========================
# Routes
# ===========================

@app.route('/', methods=['GET', 'POST'])
def index():
    ledgers = ['تقسيط', 'R-M', 'ديون نقدية']
    selected_ledger = request.args.get("ledger", "")
    query = request.args.get("query", "")

    customers = []
    if selected_ledger:
        customers = Customer.query.filter_by(ledger=selected_ledger)
        if query:
            if query.isdigit():
                customers = customers.filter(
                    (Customer.id == int(query)) |
                    (Customer.name.contains(query))
                )
            else:
                customers = customers.filter(Customer.name.contains(query))
        customers = customers.all()

    return render_template(
        "index.html",
        ledgers=ledgers,
        customers=customers,
        selected_ledger=selected_ledger,
        query=query
    )

ledger_codes = {
    "تقسيط": "A",
    "R-M": "B",
    "ديون نقدية": "C"
}
@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        notes = request.form.get("notes", "").strip()
        ledger = request.form.get("ledger", "تقسيط").strip()

        if not name:
            return "الاسم مطلوب", 400

        # 1) نحصل على حرف الدفتر
        prefix = ledger_codes.get(ledger, "X")

        # 2) نحسب عدد الزباين بهذا الدفتر
        count = Customer.query.filter_by(ledger=ledger).count()

        # 3) نولّد ID مثل A.1 — B.3 — C.10
        custom_id = f"{prefix}.{count + 1}"

        # 4) إنشاء الزبون
        new_customer = Customer(
            name=name,
            phone=phone,
            notes=notes,
            ledger=ledger,
            custom_id=custom_id
        )

        db.session.add(new_customer)
        db.session.commit()

        return redirect(url_for("customer_page", id=new_customer.id))

    # 👇👇 هاي كانت ناقصة!
    return render_template("add_customer.html")

@app.route("/delete_customer/<int:id>", methods=["POST"])
def delete_customer(id):
    customer = Customer.query.get_or_404(id)

    # حذف الأقساط والمدفوعات والكاش المرتبطة فيه
    InstallmentProduct.query.filter_by(customer_id=id).delete()
    CashDebt.query.filter_by(customer_id=id).delete()

    db.session.delete(customer)
    db.session.commit()

    return redirect(url_for("index"))

@app.route("/edit_customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)

    if request.method == "POST":
        customer.name = request.form.get("name", customer.name)
        customer.notes = request.form.get("notes", customer.notes)
        customer.phone = request.form.get("phone", customer.phone)
        customer.ledger = request.form.get("ledger", customer.ledger)

        db.session.commit()
        return redirect(url_for("customer_page", id=customer.id))

    return render_template("edit_customer.html", customer=customer)


@app.route("/customer/<int:id>")
def customer_page(id):
    customer = Customer.query.get_or_404(id)
    installment_products = InstallmentProduct.query.filter_by(customer_id=id).all()
    cash_debts = CashDebt.query.filter_by(customer_id=id).all()
    general_payments = list(customer.general_cash_payments)    

    # تجهيز قائمة دفعات لكل منتج مع المتبقي
    installment_details = []

    for product in installment_products:
        total_price = product.total_price
        initial = product.initial_payment

        remaining = total_price - initial

        payments_info = []

        # أول سطرة: السلفة إذا موجودة
        if initial > 0:
            payments_info.append({
                "amount": initial,
                "date": product.date_added,
                "remaining": remaining
            })

        # دفعات القسط
        for p in sorted(product.payments, key=lambda x: x.date_paid):
            remaining -= p.amount
            payments_info.append({
                "amount": p.amount,
                "date": p.date_paid,
                "remaining": remaining if remaining > 0 else 0
            })

        # تحديث حالة المنتج إذا خلص
        product.paid_off = (remaining <= 0)


        installment_details.append({
            "product": product,
            "payments": payments_info
        })
    db.session.commit()

    # مجموع الديون بعد طرح الدفعات المرتبطة بكل دين
    total_cash_debt = sum(
        debt.price - sum(p.amount for p in debt.payments)
        for debt in cash_debts
    )

    # جمع الدفعات العامة
    total_general_paid = sum(p.amount for p in general_payments)

    # الباقي النهائي
    remaining_cash = total_cash_debt - total_general_paid
    if remaining_cash < 0:
        remaining_cash = 0

    return render_template(
        "customer.html",
        customer=customer,
        installment_products=installment_products,
        installment_details=installment_details,   # ← أضفناها
        cash_debts=cash_debts,
        general_payments=general_payments,
        total_cash_debt=total_cash_debt,
        remaining_cash=remaining_cash
    )

# ======================
# إضافة منتج تقسيط
# ======================
@app.route("/customer/<int:id>/add_installment_product", methods=["GET", "POST"])
def add_installment_product(id):
    # نتحقق إذا الزبون موجود
    customer = Customer.query.get_or_404(id)
    # ❗ منع دفاتر النقد فقط
    if customer.ledger == "ديون نقدية":
        return "هذا الدفتر لا يحتوي على أقساط", 403

    if request.method == "POST":
        try:
            # جمع البيانات من الفورم
            name = request.form.get("name").strip()
            total_price = float(request.form.get("total_price", 0))
            initial_payment = float(request.form.get("initial_payment", 0))
            monthly_installment = float(request.form.get("monthly_installment", 0))
            date_str = request.form.get("date_added")
            date_added = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.utcnow()

            # التحقق من صحة البيانات
            if not name:
                flash("اسم المنتج مطلوب!", "error")
                return render_template("add_installment_product.html", customer_id=id)

            if total_price <= 0:
                flash("السعر الكلي يجب أن يكون أكبر من صفر!", "error")
                return render_template("add_installment_product.html", customer_id=id)

            # إنشاء المنتج
            product = InstallmentProduct(
                customer_id=customer.id,
                name=name,
                total_price=total_price,
                initial_payment=initial_payment,
                monthly_installment=monthly_installment,
                date_added=date_added
            )

            db.session.add(product)
            db.session.commit()
            flash(f"تم إضافة المنتج {name} بنجاح!", "success")
            return redirect(url_for("customer_page", id=customer.id))

        except ValueError:
            flash("تأكد من إدخال أرقام صحيحة للأسعار والأقساط.", "error")
            return render_template("add_installment_product.html", customer_id=id)

    # GET request
    return render_template("add_installment_product.html", customer_id=id)

# ======================
# حذف منتج تقسيط
# ======================
@app.route("/installment_product/<int:id>/delete", methods=["POST"])
def delete_installment_product(id):
    product = InstallmentProduct.query.get_or_404(id)
    customer = product.customer
    if customer.ledger == "ديون نقدية":
        return "هذا الدفتر لا يحتوي على أقساط", 403
    cid = product.customer_id
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for("customer_page", id=cid))


# ======================
# إضافة دفعة قسط
# ======================
@app.route("/installment_product/<int:id>/add_payment", methods=["GET", "POST"])
def add_installment_payment(id):
    product = InstallmentProduct.query.get_or_404(id)
    customer = product.customer
    if customer.ledger == "ديون نقدية":
        return "هذا الدفتر لا يحتوي على أقساط", 403

    if request.method == "POST":
        try:
            # تحويل المبلغ المدخل لـ float
            amount = float(request.form["amount"])
            
            # source ثابت إذا ما تم إدخاله
            source = request.form.get("source", "دفعة على المنتج")
            
            # التعامل مع تاريخ الدفع، إذا المستخدم حدد التاريخ نحوله لـ datetime
            date_paid_str = request.form.get("date_paid")
            if date_paid_str:
                date_paid = datetime.fromisoformat(date_paid_str)
            else:
                date_paid = datetime.utcnow()
        except (KeyError, ValueError):
            return "بيانات غير صحيحة في الفورم", 400

        # إنشاء دفعة جديدة
        payment = InstallmentPayment(
            product_id=id,
            amount=amount,
            source=source,
            date_paid=date_paid
        )
        db.session.add(payment)

        # بعد إضافة الدفعة الجديدة
        total_paid = sum(p.amount for p in product.payments) + amount
        remaining = product.total_price - product.initial_payment - total_paid

        if remaining <= 0:
            product.paid_off = True
        else:
            product.paid_off = False

        db.session.commit()
        return redirect(url_for("customer_page", id=product.customer_id))

    return render_template("add_installment_payment.html", product=product)


@app.route("/installment_payment/<int:id>/delete", methods=["POST"])
def delete_installment_payment(id):
    payment = InstallmentPayment.query.get_or_404(id)
    customer = payment.product.customer
    if customer.ledger == "ديون نقدية":
        return "هذا الدفتر لا يحتوي على أقساط", 403
    cid = payment.product.customer_id
    db.session.delete(payment)
    db.session.commit()
    return redirect(url_for("customer_page", id=cid))

# ======================
# إضافة دين نقدي
# ======================
@app.route("/customer/<int:id>/add_cash_debt", methods=["GET", "POST"])
def add_cash_debt(id):
    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        date_added = datetime.strptime(request.form["date_added"], "%Y-%m-%d")

        debt = CashDebt(
            customer_id=id,
            name=name,
            price=price,
            date_added=date_added
        )
        db.session.add(debt)
        db.session.commit()
        return redirect(url_for("customer_page", id=id))

    return render_template("add_cash_debt.html", customer_id=id, datetime=datetime)



@app.route("/cash_debt/<int:id>/delete", methods=["POST"])
def delete_cash_debt(id):
    debt = CashDebt.query.get_or_404(id)
    cid = debt.customer_id
    db.session.delete(debt)
    db.session.commit()
    return redirect(url_for("customer_page", id=cid))


# ======================
# إضافة دفعة دين نقدي
# ======================
@app.route("/cash_debt/<int:id>/add_payment", methods=["GET", "POST"])
def add_cash_debt_payment(id):
    debt = CashDebt.query.get_or_404(id)

    if request.method == "POST":
        amount = float(request.form["amount"])

        payment = CashDebtPayment(
            cash_debt_id=id,
            amount=amount
        )
        db.session.add(payment)
        db.session.commit()
        return redirect(url_for("customer_page", id=debt.customer_id))

    return render_template("add_cash_debt_payment.html", debt=debt)



@app.route("/cash_debt_payment/<int:id>/delete", methods=["POST"])
def delete_cash_debt_payment(id):
    payment = CashDebtPayment.query.get_or_404(id)
    cid = payment.debt.customer_id
    db.session.delete(payment)
    db.session.commit()
    return redirect(url_for("customer_page", id=cid))


@app.route("/customer/<int:id>/add_general_cash_payment", methods=["GET", "POST"])
def add_general_cash_payment(id):
    customer = Customer.query.get_or_404(id)

    if request.method == "POST":
        try:
            # تحويل المبلغ إلى float والتحقق منه
            amount = float(request.form.get("amount", 0))
            if amount <= 0:
                flash("المبلغ يجب أن يكون أكبر من صفر!", "error")
                return redirect(url_for("customer_page", id=id))
        except ValueError:
            flash("المبلغ غير صالح!", "error")
            return redirect(url_for("customer_page", id=id))

        # التعامل مع التاريخ
        date_paid_str = request.form.get("date_paid")
        date_paid = datetime.strptime(date_paid_str, "%Y-%m-%d") if date_paid_str else datetime.utcnow()

        # إنشاء الدفعة
        payment = GeneralCashPayment(
            customer_id=id,
            amount=amount,
            date_paid=date_paid
        )
        db.session.add(payment)
        db.session.commit()

        flash(f"تمت إضافة دفعة عامة بمبلغ {amount}$ بنجاح!", "success")
        return redirect(url_for("customer_page", id=id))

    # GET request → عرض الفورم
    return render_template("add_general_cash_payment.html", customer=customer, datetime=datetime)


# @app.route("/customer/<int:id>/invoice")
# def customer_invoice(id):
#     customer = Customer.query.get_or_404(id)

#     # جمع كل الأحداث: منتجات، ديون نقدية، دفعات عامة
#     events = []

#     # المنتجات
#     installment_products = InstallmentProduct.query.filter_by(customer_id=id).all()
#     for product in installment_products:
#         events.append({
#             "type": "product",
#             "name": product.name,
#             "amount": product.total_price,
#             "date": product.date_added
#         })
#     # الديون النقدية
#     cash_debts = customer.cash_debts

#     # ترتيب حسب التاريخ
#     events.sort(key=lambda x: x["date"])

#     # الدفعات العامة
#     general_payments = customer.general_cash_payments

#     # المجموع الكلي للباقي
#     total_cash_debts = sum(d.price for d in cash_debts)
#     total_general_paid = sum(p.amount for p in general_payments)
#     remaining = total_cash_debts - total_general_paid

#     # ترتيب الأحداث لعرضها
#     events = []


#     for debt in cash_debts:
#         events.append({
#             "type": "cash_debt",
#             "name": debt.name,
#             "amount": debt.price,
#             "date": debt.date_added
#         })

#     for payment in general_payments:
#         events.append({
#             "type": "general_payment",
#             "amount": payment.amount,
#             "date": payment.date_paid
#         })

#     events.sort(key=lambda x: x["date"])

#     running_total = 0
#     for e in events:
#         if e["type"] == "cash_debt":
#             running_total += e["amount"]
#             e["label"] = "المجموع"
#             e["balance"] = running_total
#         elif e["type"] == "general_payment":
#             running_total -= e["amount"]
#             e["label"] = "الباقي"
#             e["balance"] = running_total

#     return render_template(
#         "invoice.html",
#         customer=customer,
#         installment_products=installment_products,
#         events=events,
#         total_cash_debts=total_cash_debts,
#         remaining=remaining
#     )
@app.route("/customer/<int:id>/invoice")
def customer_invoice(id):
    customer = Customer.query.get_or_404(id)

    # 1) جمع الديون النقدية
    cash_debts = customer.cash_debts

    # 2) جمع الدفعات العامة
    general_payments = customer.general_cash_payments

    # 3) بناء قائمة الأحداث
    events = []

    # --- إضافة الديون كحركات + ---
    for debt in cash_debts:
        events.append({
            "type": "cash_debt",
            "name": debt.name,
            "amount": debt.price,
            "date": debt.date_added,
            "sign": "+"
        })

    # --- إضافة الدفعات العامة كحركات - ---
    for payment in general_payments:
        events.append({
            "type": "general_payment",
            "name": "دفعة عامة",
            "amount": payment.amount,
            "date": payment.date_paid,
            "sign": "-"
        })

    # 4) ترتيب حسب التاريخ
    events.sort(key=lambda x: x["date"])

    # 5) حساب الرصيد التراكمي
    running_total = 0
    for e in events:
        if e["sign"] == "+":
            running_total += e["amount"]
        else:
            running_total -= e["amount"]

        e["balance"] = running_total

    # 6) حساب المجاميع
    total_cash_debts = sum(d.price for d in cash_debts)
    total_general_paid = sum(p.amount for p in general_payments)

    remaining = total_cash_debts - total_general_paid
    if remaining < 0:
        remaining = 0

    return render_template(
        "invoice.html",
        customer=customer,
        events=events,
        total_cash_debts=total_cash_debts,
        total_general_paid=total_general_paid,
        remaining=remaining
    )


@app.route("/customer/<int:id>/installments_invoice")
def installments_invoice(id):
    customer = Customer.query.get_or_404(id)

    # جيب كل المنتجات اللي لسا عليها أقساط (غير مسددة)
    installment_products = [
        p for p in customer.installment_products
        if not p.paid_off
    ]

    # لو ما في منتجات غير مدفوعة
    if not installment_products:
        flash("لا يوجد منتجات تقسيط غير مسددة لهذا الزبون.", "info")
        return redirect(url_for("customer_page", id=id))

    return render_template("installments_invoice.html",
                            customer=customer,
                            products=installment_products)


@app.route("/installment_product/<int:id>/close_invoice")
def close_installment_invoice(id):
    product = InstallmentProduct.query.get_or_404(id)
    customer = product.customer

    # تجهيز جدول الدفعات والمتبقي
    total_price = product.total_price
    initial = product.initial_payment
    remaining = total_price - initial
    payments_info = []

    if initial > 0:
        payments_info.append({
            "amount": initial,
            "date": product.date_added,
            "remaining": remaining
        })

    for p in sorted(product.payments, key=lambda x: x.date_paid):
        remaining -= p.amount
        payments_info.append({
            "amount": p.amount,
            "date": p.date_paid,
            "remaining": remaining if remaining > 0 else 0
        })

    return render_template(
        "close_installment_invoice.html",
        product=product,
        customer=customer,
        payments=payments_info
    )


# ====================
# طباعة الفاتورة 
# ====================
# @app.route("/customer/<int:id>/invoice/print")
# def print_invoice(id):
#     customer = Customer.query.get_or_404(id)

#     # مجموع كل الديون النقدية
#     total_cash_debt = sum(
#     debt.price - sum(p.amount for p in debt.payments)
#     for debt in customer.cash_debts
#     )

#     # مجموع كل الدفعات العامة
#     total_general_payment = sum(p.amount for p in customer.general_cash_payments)

#     # المبلغ المتبقي
#     remaining_cash = total_cash_debt - total_general_payment
#     if remaining_cash < 0:
#         remaining_cash = 0

#     return render_template(
#         "invoice.html",
#         customer=customer,
#         cash_debts=customer.cash_debts,
#         installment_products=customer.installment_products.all(),
#         total_cash_debt=total_cash_debt,          # 🔥 مهم جداً
#         total_general_payment=total_general_payment,
#         remaining_cash=remaining_cash            # 🔥 مهم جداً
#     )

@app.route("/customer/<int:id>/invoice/print")
def print_invoice(id):
    customer = Customer.query.get_or_404(id)

    cash_debts = customer.cash_debts
    general_payments = customer.general_cash_payments

    total_cash_debts = sum(d.price for d in cash_debts)
    total_general_paid = sum(p.amount for p in general_payments)

    remaining = total_cash_debts - total_general_paid
    if remaining < 0:
        remaining = 0

    # إعداد الأحداث للطباعة بنفس منطق الفاتورة
    events = []

    for debt in cash_debts:
        events.append({
            "type": "cash_debt",
            "name": debt.name,
            "amount": debt.price,
            "date": debt.date_added,
            "sign": "+"
        })

    for payment in general_payments:
        events.append({
            "type": "general_payment",
            "name": "دفعة عامة",
            "amount": payment.amount,
            "date": payment.date_paid,
            "sign": "-"
        })

    events.sort(key=lambda x: x["date"])

    running_total = 0
    for e in events:
        running_total += e["amount"] if e["sign"] == "+" else -e["amount"]
        e["balance"] = running_total

    return render_template(
        "invoice.html",
        customer=customer,
        events=events,
        total_cash_debts=total_cash_debts,
        total_general_paid=total_general_paid,
        remaining=remaining,
        print_mode=True  # لو بدنا CSS خاص للطباعة
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
