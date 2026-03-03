from flask import Blueprint, redirect, request, session, current_app

i18n_bp = Blueprint('i18n', __name__)

@i18n_bp.route('/set-lang/<lang>')
def set_lang(lang):
    if lang in current_app.config['BABEL_SUPPORTED_LOCALES']:
        session['lang'] = lang
    return redirect(request.referrer or '/')
