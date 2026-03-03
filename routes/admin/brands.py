# routes/admin/brands.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from extensions import db
from models import Brand
from utils.admin_auth import admin_required

admin_brands_bp = Blueprint("admin_brands", __name__, url_prefix="/admin/brands")

ALLOWED_DEPTS = {"electrical", "linens", "crystal"}


@admin_brands_bp.route("/", methods=["GET", "POST"])
@admin_required
def brands_list():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        code = (request.form.get("code") or "").strip().upper()

        department = (request.form.get("department") or "electrical").strip().lower()
        if department not in ALLOWED_DEPTS:
            department = "electrical"

        if not name or not code:
            flash(_("الاسم والكود مطلوبان"), "danger")
            return redirect(url_for("admin_brands.brands_list"))

        existing = Brand.query.filter_by(code=code, department=department).first()
        if existing:
            flash(_("هذه الماركة موجودة مسبقًا في هذا القسم. (ID: %(id)s)", id=existing.id), "warning")
            return redirect(url_for("admin_brands.brands_list"))

        b = Brand(name=name, code=code, department=department)
        db.session.add(b)
        db.session.commit()
        flash(_("تمت إضافة الماركة ✅"), "success")
        return redirect(url_for("admin_brands.brands_list"))

    brands = Brand.query.order_by(Brand.department.asc(), Brand.name.asc()).all()
    return render_template("admin/brands.html", brands=brands)


@admin_brands_bp.route("/<int:brand_id>/delete", methods=["POST"])
@admin_required
def delete_brand(brand_id: int):
    b = Brand.query.get_or_404(brand_id)
    db.session.delete(b)
    db.session.commit()
    flash(_("تم حذف الماركة 🗑️"), "success")
    return redirect(url_for("admin_brands.brands_list"))
