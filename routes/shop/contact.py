from flask import render_template, request, flash, redirect
from flask_babel import gettext as _
from datetime import datetime

def register(app):
    @app.get("/shop/contact")
    def shop_contact_view():
        return render_template("shop/contact.html")

    @app.post("/shop/contact")
    def shop_contact_post():
        # (اختياري) بس لتجربة الفورم بدون إرسال حقيقي
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        message = (request.form.get("message") or "").strip()

        if not message:
            flash(_("اكتب رسالتك أولاً."), "danger")
            return redirect("/shop/contact")

        # هون لاحقاً فيك تربطه بواتساب/إيميل/DB.. حالياً بس فلاش
        flash(_("تم استلام رسالتك ✅ سنتواصل معك قريباً."), "success")
        return redirect("/shop/contact")