# context_processors.py
from flask import current_app, session
from i18n import get_locale
from models import User

def inject_i18n():
    return {
        'get_locale': lambda: get_locale(current_app),
    }


def inject_storefront_user():
    user = None
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)

    return {
        "current_user": user,
        "is_logged_in": bool(user),
        "can_view_prices": bool(user and user.can_view_prices),
    }

from flask import current_app


