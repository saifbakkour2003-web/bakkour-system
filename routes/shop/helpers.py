# routes/shop/helpers.py
from functools import wraps
from flask import session, redirect, flash
from flask_babel import gettext as _
from models import User


def get_shop_user():
    """Return logged-in shop user or None (and cleanup session if invalid)."""
    uid = session.get("shop_user_id")
    if not uid:
        return None

    user = User.query.get(uid)
    if not user:
        session.pop("shop_user_id", None)
        return None

    return user


def shop_login_required(view_func):
    """Require a logged-in shop user."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_shop_user()
        if not user:
            return redirect("/shop/login")
        return view_func(user, *args, **kwargs)
    return wrapper


def shop_active_or_admin_required(view_func):
    """
    Require user to be active (buyer) OR admin.
    If pending -> show friendly message, but still allow rendering.
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_shop_user()
        if not user:
            return redirect("/shop/login")

        if user.status == "blocked":
            flash(_("حسابك موقوف. تواصل معنا."), "danger")
            session.pop("shop_user_id", None)
            return redirect("/shop/login")

        return view_func(user, *args, **kwargs)
    return wrapper


def is_active_or_admin(user: User) -> bool:
    return (user.role == "admin") or (user.status == "active")
