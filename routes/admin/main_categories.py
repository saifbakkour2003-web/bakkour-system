from flask import Blueprint, render_template, redirect, url_for, flash
from flask_babel import gettext as _
from models import MainCategory
from utils.admin_auth import admin_required

admin_main_categories_bp = Blueprint(
    "admin_main_categories",
    __name__,
    url_prefix="/admin/main-categories"
)

FIXED_DEPARTMENTS = [
    {
        "department": "electrical",
        "name": "كهربائيات",
        "name_tr": "Elektrik",
        "code_prefix": "ELE",
    },
    {
        "department": "linens",
        "name": "بياضات",
        "name_tr": "Tekstil",
        "code_prefix": "LIN",
    },
    {
        "department": "crystal",
        "name": "بلوريات",
        "name_tr": "Kristal",
        "code_prefix": "CRY",
    },
]


@admin_main_categories_bp.get("/")
@admin_required
def list_main_categories():
    """
    Main categories are now treated as fixed system departments.
    We still read from DB for compatibility, but the UI is read-only.
    """
    categories = MainCategory.query.order_by(MainCategory.id.asc()).all()

    return render_template(
        "admin/categories/main_categories/list.html",
        categories=categories,
        fixed_departments=FIXED_DEPARTMENTS
    )


@admin_main_categories_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_main_category():
    flash(_("التصنيفات الرئيسية أصبحت ثابتة بالنظام ولا يمكن إضافة قسم جديد من الواجهة."), "warning")
    return redirect(url_for("admin_main_categories.list_main_categories"))


@admin_main_categories_bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_main_category(category_id: int):
    flash(_("التصنيفات الرئيسية أصبحت ثابتة بالنظام ولا يمكن تعديلها من الواجهة."), "warning")
    return redirect(url_for("admin_main_categories.list_main_categories"))


@admin_main_categories_bp.post("/<int:category_id>/delete")
@admin_required
def delete_main_category(category_id: int):
    flash(_("التصنيفات الرئيسية أصبحت ثابتة بالنظام ولا يمكن حذفها من الواجهة."), "warning")
    return redirect(url_for("admin_main_categories.list_main_categories"))