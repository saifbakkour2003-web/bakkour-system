# routes/admin/sub_categories.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from extensions import db
from models import MainCategory, SubCategory, Property, Product
from utils.admin_auth import admin_required

admin_sub_categories_bp = Blueprint(
    "admin_sub_categories",
    __name__,
    url_prefix="/admin/sub-categories"
)


@admin_sub_categories_bp.get("/")
@admin_required
def list_sub_categories():
    main_id = request.args.get("main", type=int)

    q = SubCategory.query.join(MainCategory)
    if main_id:
        q = q.filter(SubCategory.main_category_id == main_id)

    sub_categories = q.order_by(SubCategory.id.asc()).all()
    main_categories = MainCategory.query.order_by(MainCategory.name.asc()).all()

    return render_template(
        "admin/categories/sub_categories/list.html",
        sub_categories=sub_categories,
        main_categories=main_categories,
        selected_main_id=main_id
    )


@admin_sub_categories_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_sub_category():
    main_categories = MainCategory.query.order_by(MainCategory.name).all()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        code_prefix = (request.form.get("code_prefix") or "").strip().upper()
        main_category_id = request.form.get("main_category_id")

        if not name or not code_prefix or not main_category_id:
            flash(_("كل الحقول مطلوبة"), "danger")
            return redirect(request.url)

        main = MainCategory.query.get_or_404(int(main_category_id))

        sub = SubCategory(
            name=name,
            name_tr=name_tr,
            code_prefix=code_prefix,
            main_category_id=main.id,
            department=(main.department or "electrical")
        )

        db.session.add(sub)
        db.session.commit()

        flash(_("تمت إضافة التصنيف الفرعي بنجاح ✅"), "success")
        return redirect(url_for("admin_sub_categories.list_sub_categories"))

    return render_template(
        "admin/categories/sub_categories/add.html",
        main_categories=main_categories
    )


@admin_sub_categories_bp.get("/<int:sub_id>/properties")
@admin_required
def get_sub_category_properties(sub_id: int):
    properties = Property.query.filter_by(sub_category_id=sub_id).all()

    result = []
    for p in properties:
        item = {
            "id": p.id,
            "name": p.name,
            "input_type": p.input_type,
            "is_required": p.is_required,
            "values": []
        }
        if p.input_type == "select":
            item["values"] = [v.value for v in p.values]
        result.append(item)

    return jsonify(result)


@admin_sub_categories_bp.route("/<int:sub_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_sub_category(sub_id: int):
    sub = SubCategory.query.get_or_404(sub_id)
    main_categories = MainCategory.query.order_by(MainCategory.name).all()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        code_prefix = (request.form.get("code_prefix") or "").strip().upper()
        main_category_id = request.form.get("main_category_id")

        if not name or not code_prefix or not main_category_id:
            flash(_("كل الحقول مطلوبة"), "danger")
            return redirect(request.url)

        main = MainCategory.query.get_or_404(int(main_category_id))

        sub.name = name
        sub.name_tr = name_tr
        sub.code_prefix = code_prefix
        sub.main_category_id = main.id
        sub.department = (main.department or "electrical")

        db.session.commit()
        flash(_("تم تعديل التصنيف الفرعي بنجاح ✅"), "success")
        return redirect(url_for("admin_sub_categories.list_sub_categories"))

    return render_template(
        "admin/categories/sub_categories/edit.html",
        sub=sub,
        main_categories=main_categories
    )


@admin_sub_categories_bp.post("/<int:sub_id>/delete")
@admin_required
def delete_sub_category(sub_id: int):
    sub = SubCategory.query.get_or_404(sub_id)

    if Product.query.filter_by(sub_category_id=sub.id).first():
        flash(_("لا يمكن حذف تصنيف يحتوي منتجات ❌"), "warning")
        return redirect(url_for("admin_sub_categories.list_sub_categories"))

    if Property.query.filter_by(sub_category_id=sub.id).first():
        flash(_("لا يمكن حذف تصنيف يحتوي خصائص ❌"), "warning")
        return redirect(url_for("admin_sub_categories.list_sub_categories"))

    db.session.delete(sub)
    db.session.commit()

    flash(_("تم حذف التصنيف الفرعي 🗑️"), "success")
    return redirect(url_for("admin_sub_categories.list_sub_categories"))
