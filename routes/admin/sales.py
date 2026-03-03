# routes/admin/sales.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_babel import gettext as _
from extensions import db
from models import Sale, Product, Customer
from datetime import datetime, date, timedelta
from sqlalchemy import func
from utils.stock_utils import try_deduct_stock
from utils.admin_auth import admin_required


sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


@sales_bp.route("/add/<int:product_id>", methods=["GET", "POST"])
@admin_required
def add_sale(product_id):
    product = Product.query.get_or_404(product_id)
    customers = Customer.query.order_by(Customer.name).all()

    if request.method == "POST":
        sale_type = request.form.get("sale_type")
        sell_price = float(request.form.get("sell_price") or 0)
        customer_id = request.form.get("customer_id") or None

        sale = Sale(
            product_id=product.id,
            customer_id=int(customer_id) if customer_id else None,
            sale_type=sale_type,
            sell_price=sell_price,
            cost_price=product.capital_price,
            date_created=datetime.utcnow()
        )

        db.session.add(sale)
        if current_app.config.get("STOCK_DEDUCT_ON_SALE"):
            try_deduct_stock(product, 1)
        db.session.commit()

        flash(_("تم تسجيل البيع بنجاح 💰"), "success")
        return redirect(url_for("products.products_list"))

    return render_template("sales/add.html", product=product, customers=customers)


@sales_bp.route("/profits")
@admin_required
def profits_report():
    # view: month/day/range
    view = (request.args.get("view") or "month").strip()
    today = date.today()

    # قيم افتراضية
    day_str = (request.args.get("day") or today.strftime("%Y-%m-%d")).strip()
    month_str = (request.args.get("month") or today.strftime("%Y-%m")).strip()
    from_str = (request.args.get("from") or "").strip()
    to_str = (request.args.get("to") or "").strip()

    def dt_start_end_for_day(d: date):
        start = datetime(d.year, d.month, d.day, 0, 0, 0)
        end = start + timedelta(days=1)
        return start, end

    def dt_start_end_for_month(y: int, m: int):
        start = datetime(y, m, 1, 0, 0, 0)
        if m == 12:
            end = datetime(y + 1, 1, 1, 0, 0, 0)
        else:
            end = datetime(y, m + 1, 1, 0, 0, 0)
        return start, end

    start_dt = None
    end_dt = None

    try:
        if view == "day":
            d = datetime.strptime(day_str, "%Y-%m-%d").date()
            start_dt, end_dt = dt_start_end_for_day(d)

        elif view == "range":
            if not from_str or not to_str:
                start_dt, end_dt = dt_start_end_for_day(today)
            else:
                d1 = datetime.strptime(from_str, "%Y-%m-%d").date()
                d2 = datetime.strptime(to_str, "%Y-%m-%d").date()
                if d2 < d1:
                    d1, d2 = d2, d1
                start_dt = datetime(d1.year, d1.month, d1.day, 0, 0, 0)
                end_dt = datetime(d2.year, d2.month, d2.day, 0, 0, 0) + timedelta(days=1)

        else:
            y, m = month_str.split("-")
            y = int(y)
            m = int(m)
            start_dt, end_dt = dt_start_end_for_month(y, m)

    except Exception:
        view = "month"
        start_dt, end_dt = dt_start_end_for_month(today.year, today.month)
        month_str = today.strftime("%Y-%m")

    # ===============================
    # جلب المبيعات
    # ===============================

    q = Sale.query.filter(
        Sale.date_created >= start_dt,
        Sale.date_created < end_dt
    )

    sales = q.order_by(Sale.date_created.desc()).all()

    total_revenue = sum(float(s.sell_price or 0) for s in sales)
    total_cost = sum(float(s.cost_price or 0) for s in sales)
    total_profit = sum(
        (float(s.sell_price or 0) - float(s.cost_price or 0))
        for s in sales
    )

    # ===============================
    # تجميع يومي (Postgres + SQLite)
    # ===============================

    dialect = db.engine.dialect.name

    if dialect == "postgresql":
        day_expr = func.date_trunc("day", Sale.date_created)
    else:
        day_expr = func.strftime("%Y-%m-%d", Sale.date_created)

    grouped = (
        db.session.query(
            day_expr.label("day"),
            func.count(Sale.id).label("count"),
            func.sum(Sale.sell_price).label("revenue"),
            func.sum(Sale.cost_price).label("cost"),
        )
        .filter(
            Sale.date_created >= start_dt,
            Sale.date_created < end_dt
        )
        .group_by(day_expr)
        .order_by(day_expr.desc())
        .all()
    )

    daily_rows = []

    for r in grouped:
        revenue = float(r.revenue or 0)
        cost = float(r.cost or 0)

        # توحيد شكل التاريخ
        if hasattr(r.day, "strftime"):
            day_key = r.day.strftime("%Y-%m-%d")
        else:
            day_key = str(r.day)

        daily_rows.append({
            "day": day_key,
            "count": int(r.count or 0),
            "revenue": revenue,
            "cost": cost,
            "profit": revenue - cost
        })

    return render_template(
        "sales/profits.html",
        sales=sales,
        total_profit=round(total_profit, 2),
        total_revenue=round(total_revenue, 2),
        total_cost=round(total_cost, 2),
        daily_rows=daily_rows,
        view=view,
        day_str=day_str,
        month_str=month_str,
        from_str=from_str,
        to_str=to_str
    )