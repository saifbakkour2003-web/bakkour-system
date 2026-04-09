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

ALLOWED_DEPTS = {"electrical", "linens", "crystal"}

DEPT_LABELS = {
    "electrical": _("كهربائيات"),
    "linens": _("بياضات"),
    "crystal": _("بلوريات"),
}

FIXED_MAIN_CATEGORY_DATA = {
    "electrical": {
        "name": "كهربائيات",
        "name_tr": "Elektrik",
        "code_prefix": "ELE",
    },
    "linens": {
        "name": "بياضات",
        "name_tr": "Tekstil",
        "code_prefix": "LIN",
    },
    "crystal": {
        "name": "بلوريات",
        "name_tr": "Kristal",
        "code_prefix": "CRY",
    },
}


def normalize_dept(dept: str | None) -> str | None:
    d = (dept or "").strip().lower()
    return d if d in ALLOWED_DEPTS else None


def get_or_create_fixed_main_category(dept: str) -> MainCategory:
    """
    Keep MainCategory as a legacy backing table, but treat it as fixed.
    We ensure one canonical row exists per department.
    """
    dept = normalize_dept(dept)
    if not dept:
        raise ValueError("Invalid department")

    existing = (
        MainCategory.query
        .filter(MainCategory.department == dept)
        .order_by(MainCategory.id.asc())
        .first()
    )

    data = FIXED_MAIN_CATEGORY_DATA[dept]

    if existing:
        # normalize the canonical row
        existing.name = data["name"]
        existing.name_tr = data["name_tr"]
        existing.code_prefix = data["code_prefix"]
        db.session.flush()
        return existing

    obj = MainCategory(
        name=data["name"],
        name_tr=data["name_tr"],
        code_prefix=data["code_prefix"],
        department=dept
    )
    db.session.add(obj)
    db.session.flush()
    return obj


@admin_sub_categories_bp.get("/")
@admin_required
def list_sub_categories():
    dept = normalize_dept(request.args.get("dept"))

    q = SubCategory.query

    if dept:
        q = q.filter(SubCategory.department == dept)

    sub_categories = q.order_by(SubCategory.id.asc()).all()

    return render_template(
        "admin/categories/sub_categories/list.html",
        sub_categories=sub_categories,
        selected_dept=dept,
        dept_labels=DEPT_LABELS
    )


@admin_sub_categories_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_sub_category():
    dept = normalize_dept(request.args.get("dept"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        code_prefix = (request.form.get("code_prefix") or "").strip().upper()
        department = normalize_dept(request.form.get("department"))

        if not name or not code_prefix or not department:
            flash(_("كل الحقول مطلوبة"), "danger")
            return redirect(request.url)

        main = get_or_create_fixed_main_category(department)

        sub = SubCategory(
            name=name,
            name_tr=name_tr,
            code_prefix=code_prefix,
            main_category_id=main.id,   # legacy compatibility
            department=department
        )

        db.session.add(sub)
        db.session.commit()

        flash(_("تمت إضافة التصنيف الفرعي بنجاح ✅"), "success")
        return redirect(url_for("admin_sub_categories.list_sub_categories", dept=department))

    return render_template(
        "admin/categories/sub_categories/add.html",
        selected_dept=dept,
        dept_labels=DEPT_LABELS
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

    dept = normalize_dept(request.args.get("dept")) or normalize_dept(sub.department)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        code_prefix = (request.form.get("code_prefix") or "").strip().upper()
        department = normalize_dept(request.form.get("department"))

        if not name or not code_prefix or not department:
            flash(_("كل الحقول مطلوبة"), "danger")
            return redirect(request.url)

        main = get_or_create_fixed_main_category(department)

        sub.name = name
        sub.name_tr = name_tr
        sub.code_prefix = code_prefix
        sub.department = department
        sub.main_category_id = main.id  # legacy compatibility

        db.session.commit()

        flash(_("تم تعديل التصنيف الفرعي بنجاح ✅"), "success")
        return redirect(url_for("admin_sub_categories.list_sub_categories", dept=department))

    return render_template(
        "admin/categories/sub_categories/edit.html",
        sub=sub,
        selected_dept=dept,
        dept_labels=DEPT_LABELS
    )


@admin_sub_categories_bp.post("/<int:sub_id>/delete")
@admin_required
def delete_sub_category(sub_id: int):
    sub = SubCategory.query.get_or_404(sub_id)

    if Product.query.filter_by(sub_category_id=sub.id).first():
        flash(_("لا يمكن حذف تصنيف يحتوي منتجات ❌"), "warning")
        return redirect(url_for("admin_sub_categories.list_sub_categories", dept=sub.department))

    if Property.query.filter_by(sub_category_id=sub.id).first():
        flash(_("لا يمكن حذف تصنيف يحتوي خصائص ❌"), "warning")
        return redirect(url_for("admin_sub_categories.list_sub_categories", dept=sub.department))

    dept = sub.department

    db.session.delete(sub)
    db.session.commit()

    flash(_("تم حذف التصنيف الفرعي 🗑️"), "success")
    return redirect(url_for("admin_sub_categories.list_sub_categories", dept=dept))