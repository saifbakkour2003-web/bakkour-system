# i18n.py
from flask import request, session
from flask_babel import get_locale as babel_get_locale
from extensions import babel


def get_locale(app):
    # 1) query param
    lang = request.args.get('lang')
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        session['lang'] = lang

    # 2) session
    lang = session.get('lang')
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        return lang

    # 3) default
    return app.config['BABEL_DEFAULT_LOCALE']


def pick_lang(ar_value, tr_value):
    lang = str(babel_get_locale())
    if lang.startswith("tr") and tr_value:
        return tr_value
    return ar_value


def init_i18n(app):
    babel.init_app(app, locale_selector=lambda: get_locale(app))

    # تسجيل helper داخل Jinja
    app.jinja_env.globals["pick_lang"] = pick_lang
