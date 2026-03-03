# routes/admin/main_categories.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from extensions import db
from models import MainCategory, SubCategory
from utils.admin_auth import admin_required

admin_main_categories_bp = Blueprint(
    "admin_main_categories",
    __name__,
    url_prefix="/admin/main-categories"
)


@admin_main_categories_bp.get("/")
@admin_required
def list_main_categories():
    categories = MainCategory.query.order_by(MainCategory.id.desc()).all()
    return render_template(
        "admin/categories/main_categories/list.html",
        categories=categories
    )


@admin_main_categories_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_main_category():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        code_prefix = (request.form.get("code_prefix") or "").strip()

        if not name or not code_prefix:
            flash(_("كل الحقول مطلوبة"), "danger")
            return redirect(request.url)

        exists = MainCategory.query.filter_by(name=name).first()
        if exists:
            flash(_("هذا التصنيف موجود مسبقًا"), "warning")
            return redirect(request.url)

        category = MainCategory(
            name=name,
            name_tr=name_tr,
            code_prefix=code_prefix.upper()
        )

        db.session.add(category)
        db.session.commit()

        flash(_("تمت إضافة التصنيف الرئيسي بنجاح ✅"), "success")
        return redirect(url_for("admin_main_categories.list_main_categories"))

    return render_template("admin/categories/main_categories/add.html")


@admin_main_categories_bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_main_category(category_id: int):
    category = MainCategory.query.get_or_404(category_id)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        code_prefix = (request.form.get("code_prefix") or "").strip()

        if not name or not code_prefix:
            flash(_("كل الحقول مطلوبة"), "danger")
            return redirect(request.url)

        category.name = name
        category.name_tr = name_tr
        category.code_prefix = code_prefix.upper()

        db.session.commit()
        flash(_("تم تعديل التصنيف بنجاح ✅"), "success")
        return redirect(url_for("admin_main_categories.list_main_categories"))

    return render_template(
        "admin/categories/main_categories/edit.html",
        category=category
    )


@admin_main_categories_bp.post("/<int:category_id>/delete")
@admin_required
def delete_main_category(category_id: int):
    category = MainCategory.query.get_or_404(category_id)

    if SubCategory.query.filter_by(main_category_id=category.id).first():
        flash(_("لا يمكن حذف تصنيف يحتوي تصنيفات فرعية ❌"), "warning")
        return redirect(url_for("admin_main_categories.list_main_categories"))

    db.session.delete(category)
    db.session.commit()

    flash(_("تم حذف التصنيف 🗑️"), "success")
    return redirect(url_for("admin_main_categories.list_main_categories"))
