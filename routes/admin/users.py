# routes/admin/users.py
from flask import Blueprint, render_template, request, redirect, flash
from flask_babel import gettext as _
from models import db, User, Customer
from utils.admin_auth import admin_required

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/admin/users")


@admin_users_bp.get("/")
@admin_required
def admin_users_redirect():
    return redirect("/admin/users/pending")


@admin_users_bp.get("/pending")
@admin_required
def admin_users_pending():
    pending = (
        User.query
        .filter_by(role="buyer", status="pending")
        .order_by(User.id.desc())
        .all()
    )
    return render_template("admin/users_pending.html", pending=pending)


@admin_users_bp.get("/manage")
@admin_required
def admin_users_manage():
    users = User.query.order_by(User.id.desc()).all()
    return render_template("admin/users_manage.html", users=users)


@admin_users_bp.post("/<int:user_id>/approve")
@admin_required
def admin_approve_user(user_id: int):
    u = User.query.get_or_404(user_id)
    u.status = "active"
    db.session.commit()

    flash(_("تم تفعيل الحساب ✅"), "success")
    return redirect("/admin/users/pending")


@admin_users_bp.post("/<int:user_id>/block")
@admin_required
def admin_block_user(user_id: int):
    u = User.query.get_or_404(user_id)
    u.status = "blocked"
    db.session.commit()
    flash(_("تم حظر الحساب"), "info")
    return redirect("/admin/users/manage")


@admin_users_bp.post("/<int:user_id>/unblock")
@admin_required
def admin_unblock_user(user_id: int):
    u = User.query.get_or_404(user_id)
    u.status = "active"
    db.session.commit()
    flash(_("تم إلغاء الحظر ✅"), "success")
    return redirect("/admin/users/manage")


@admin_users_bp.post("/<int:user_id>/toggle-admin")
@admin_required
def admin_toggle_admin(user_id: int):
    u = User.query.get_or_404(user_id)

    if u.role == "admin":
        u.role = "buyer"
        flash(_("تم إزالة صلاحية الأدمن"), "info")
    else:
        u.role = "admin"
        u.status = "active"
        flash(_("تم منح صلاحية الأدمن ✅"), "success")

    db.session.commit()
    return redirect("/admin/users/manage")


@admin_users_bp.post("/<int:user_id>/link-customer")
@admin_required
def admin_link_customer(user_id: int):
    u = User.query.get_or_404(user_id)

    code = (request.form.get("customer_ref_code") or "").strip()
    if not code:
        u.customer_ref_code = None
        db.session.commit()
        flash(_("تم إزالة الربط"), "info")
        return redirect("/admin/users/manage")

    c = Customer.query.filter_by(custom_id=code).first()
    if not c:
        flash(_("كود الزبون غير صحيح (مثال: B.1)"), "danger")
        return redirect("/admin/users/manage")

    u.customer_ref_code = code
    db.session.commit()
    flash(_("تم ربط الحساب بصفحة الزبون ✅"), "success")
    return redirect("/admin/users/manage")
