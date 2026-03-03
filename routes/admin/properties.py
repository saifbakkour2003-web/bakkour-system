# routes/admin/properties.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from extensions import db
from models import Property, SubCategory, PropertyValue, ProductProperty
from utils.admin_auth import admin_required

admin_properties_bp = Blueprint(
    "admin_properties",
    __name__,
    url_prefix="/admin/categories/properties"
)

ALLOWED_DEPTS = {"electrical", "linens", "crystal"}


def get_dept(default="electrical"):
    dept = (request.args.get("dept") or default).strip().lower()
    if dept not in ALLOWED_DEPTS:
        dept = default
    return dept


def get_dept_from_form(default="electrical"):
    dept = (request.form.get("department") or default).strip().lower()
    if dept not in ALLOWED_DEPTS:
        dept = default
    return dept


@admin_properties_bp.get("/")
@admin_required
def list_properties():
    dept = get_dept(default="electrical")

    properties = (
        Property.query
        .filter(Property.department == dept)
        .order_by(Property.id.desc())
        .all()
    )

    return render_template(
        "admin/categories/properties/list.html",
        properties=properties,
        dept=dept
    )


@admin_properties_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_property():
    dept = get_dept(default="electrical")

    sub_categories = (
        SubCategory.query
        .filter(SubCategory.department == dept)
        .order_by(SubCategory.name)
        .all()
    )

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        input_type = request.form.get("input_type")
        is_required = bool(request.form.get("is_required"))
        is_global = bool(request.form.get("is_global"))

        department = get_dept_from_form(default=dept)
        sub_category_ids = request.form.getlist("sub_category_ids")

        if not name or not input_type:
            flash(_("اسم الخاصية ونوع الإدخال مطلوبان"), "danger")
            return redirect(request.url)

        if (not is_global) and (len(sub_category_ids) == 0):
            flash(_("اختر تصنيفًا فرعيًا واحدًا على الأقل أو فعّل خيار (خاصية عامة للقسم)"), "danger")
            return redirect(request.url)

        legacy_sub = sub_categories[0] if sub_categories else SubCategory.query.first()

        prop = Property(
            name=name,
            name_tr=name_tr,
            input_type=input_type,
            is_required=is_required,
            is_global=is_global,
            department=department,
            sub_category_id=legacy_sub.id if legacy_sub else None
        )

        db.session.add(prop)
        db.session.flush()

        if is_global:
            prop.sub_categories = []
        else:
            selected_subs = (
                SubCategory.query
                .filter(SubCategory.department == department)
                .filter(SubCategory.id.in_(sub_category_ids))
                .all()
            )

            if not selected_subs:
                db.session.rollback()
                flash(_("التصنيفات المختارة غير صالحة لهذا القسم"), "danger")
                return redirect(request.url)

            prop.sub_categories = selected_subs

        db.session.commit()
        flash(_("تمت إضافة الخاصية بنجاح ✅"), "success")
        return redirect(url_for("admin_properties.list_properties", dept=department))

    return render_template(
        "admin/categories/properties/add.html",
        sub_categories=sub_categories,
        dept=dept
    )


@admin_properties_bp.route("/<int:property_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_property(property_id: int):
    prop = Property.query.get_or_404(property_id)
    dept = get_dept(default=(prop.department or "electrical"))

    sub_categories = (
        SubCategory.query
        .filter(SubCategory.department == dept)
        .order_by(SubCategory.name)
        .all()
    )

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        prop.name_tr = (request.form.get("name_tr") or "").strip() or None
        input_type = request.form.get("input_type")
        is_required = bool(request.form.get("is_required"))
        is_global = bool(request.form.get("is_global"))

        department = get_dept_from_form(default=dept)
        sub_category_ids = request.form.getlist("sub_category_ids")

        if not name or not input_type:
            flash(_("اسم الخاصية ونوع الإدخال مطلوبان"), "danger")
            return redirect(request.url)

        if (not is_global) and (len(sub_category_ids) == 0):
            flash(_("اختر تصنيفًا فرعيًا واحدًا على الأقل أو فعّل خيار (خاصية عامة للقسم)"), "danger")
            return redirect(request.url)

        if prop.input_type == "select" and input_type != "select":
            PropertyValue.query.filter_by(property_id=prop.id).delete()

        prop.name = name
        prop.input_type = input_type
        prop.is_required = is_required
        prop.is_global = is_global
        prop.department = department

        legacy_sub = sub_categories[0] if sub_categories else SubCategory.query.first()
        if legacy_sub:
            prop.sub_category_id = legacy_sub.id

        if is_global:
            prop.sub_categories = []
        else:
            selected_subs = (
                SubCategory.query
                .filter(SubCategory.department == department)
                .filter(SubCategory.id.in_(sub_category_ids))
                .all()
            )

            if not selected_subs:
                db.session.rollback()
                flash(_("التصنيفات المختارة غير صالحة لهذا القسم"), "danger")
                return redirect(request.url)

            prop.sub_categories = selected_subs

        db.session.commit()
        flash(_("تم تعديل الخاصية بنجاح ✅"), "success")
        return redirect(url_for("admin_properties.list_properties", dept=department))

    selected_ids = [s.id for s in prop.sub_categories]
    return render_template(
        "admin/categories/properties/edit.html",
        prop=prop,
        sub_categories=sub_categories,
        selected_ids=selected_ids,
        dept=dept
    )


@admin_properties_bp.post("/<int:property_id>/delete")
@admin_required
def delete_property(property_id: int):
    prop = Property.query.get_or_404(property_id)
    dept = prop.department or "electrical"

    PropertyValue.query.filter_by(property_id=prop.id).delete()
    ProductProperty.query.filter_by(property_id=prop.id).delete()

    db.session.delete(prop)
    db.session.commit()

    flash(_("تم حذف الخاصية 🗑️"), "success")
    return redirect(url_for("admin_properties.list_properties", dept=dept))


@admin_properties_bp.route("/<int:property_id>/values", methods=["GET", "POST"])
@admin_required
def manage_values(property_id: int):
    prop = Property.query.get_or_404(property_id)
    dept = prop.department or "electrical"

    if prop.input_type != "select":
        flash(_("هذه الخاصية ليست من نوع (قائمة). إذا بدك قيم جاهزة غيّر نوعها إلى select."), "info")
        values = PropertyValue.query.filter_by(property_id=prop.id).order_by(PropertyValue.id.desc()).all()
        return render_template(
            "admin/categories/properties/values.html",
            prop=prop,
            values=values,
            readonly=True,
            dept=dept
        )

    if request.method == "POST":
        value = (request.form.get("value") or "").strip()
        value_tr = (request.form.get("value_tr") or "").strip() or None
        if not value:
            flash(_("أدخل قيمة"), "danger")
            return redirect(request.url)

        exists = PropertyValue.query.filter_by(property_id=prop.id, value=value).first()
        if exists:
            flash(_("هذه القيمة موجودة مسبقًا"), "warning")
            return redirect(request.url)

        db.session.add(PropertyValue(property_id=prop.id, value=value, value_tr=value_tr))
        db.session.commit()
        flash(_("تمت إضافة القيمة ✅"), "success")
        return redirect(request.url)

    values = PropertyValue.query.filter_by(property_id=prop.id).order_by(PropertyValue.id.desc()).all()
    return render_template(
        "admin/categories/properties/values.html",
        prop=prop,
        values=values,
        readonly=False,
        dept=dept
    )


@admin_properties_bp.post("/values/<int:value_id>/delete")
@admin_required
def delete_value(value_id: int):
    pv = PropertyValue.query.get_or_404(value_id)
    prop_id = pv.property_id
    prop = Property.query.get(prop_id)
    dept = (prop.department if prop else "electrical") or "electrical"

    db.session.delete(pv)
    db.session.commit()
    flash(_("تم حذف القيمة 🗑️"), "success")
    return redirect(url_for("admin_properties.manage_values", property_id=prop_id, dept=dept))
