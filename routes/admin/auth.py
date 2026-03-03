# routes/admin/auth.py
from flask import Blueprint, render_template, request, redirect, session, flash
from flask_babel import gettext as _
from models import User

admin_auth_bp = Blueprint("admin_auth", __name__, url_prefix="/admin")

@admin_auth_bp.get("/login")
def admin_login_view():
    return render_template("admin/login.html")

@admin_auth_bp.post("/login")
def admin_login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password) or user.role != "admin":
        flash(_("بيانات الأدمن غير صحيحة."), "danger")
        return redirect("/admin/login")

    session["admin_user_id"] = user.id
    flash(_("تم تسجيل الدخول للأدمن ✅"), "success")

    next_url = request.args.get("next") or "/"
    return redirect(next_url)

@admin_auth_bp.get("/logout")
def admin_logout():
    session.pop("admin_user_id", None)
    flash(_("تم تسجيل خروج الأدمن"), "info")
    return redirect("/admin/login")