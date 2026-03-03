# utils/admin_auth.py
from functools import wraps
from flask import session, redirect, flash, request, g
from flask_babel import gettext as _
from models import User

ADMIN_SESSION_KEY = "admin_user_id"


def get_admin_user():
    uid = session.get(ADMIN_SESSION_KEY)
    if not uid:
        return None
    user = User.query.get(uid)
    if not user:
        session.pop(ADMIN_SESSION_KEY, None)
        return None
    return user


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        admin_id = session.get("admin_user_id")
        if not admin_id:
            flash(_("سجّل دخول كأدمن أولاً."), "warning")
            return redirect("/admin/login?next=" + (request.path or "/admin"))

        admin_user = User.query.get(admin_id)
        if not admin_user or admin_user.role != "admin":
            session.pop("admin_user_id", None)
            flash(_("ليس لديك صلاحية للدخول للأدمن."), "danger")
            return redirect("/admin/login")

        # نخليه متاح بالقوالب
        g.admin_user = admin_user
        return view_func(*args, **kwargs)
    return wrapper
