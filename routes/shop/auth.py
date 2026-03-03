# routes/shop/auth.py
from datetime import datetime

from flask import render_template, request, redirect, session, flash, g
from flask_babel import gettext as _
from models import User, db, Coupon , UserCoupon

from utils.coupons import auto_claim_first_available


def register(app):

    # --- helper: current shop user (session-based) ---
    @app.before_request
    def load_shop_user():
        """
        يخلي المستخدم متاح داخل templates عبر g.shop_user
        بناءً على session['shop_user_id'].
        """
        uid = session.get("shop_user_id")
        g.shop_user = User.query.get(uid) if uid else None

    @app.context_processor
    def inject_shop_user():
        """
        يضيف متغيرات جاهزة لكل القوالب:
        - shop_user
        - is_shop_logged_in
        """
        return {
            "shop_user": getattr(g, "shop_user", None),
            "is_shop_logged_in": bool(getattr(g, "shop_user", None)),
        }

    # ------------------- LOGIN -------------------
    @app.get("/shop/login")
    def shop_login_view():
        return render_template("shop/login.html")

    @app.post("/shop/login")
    def shop_login_post():
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash(_("يرجى تعبئة جميع الحقول"), "danger")
            return redirect("/shop/login")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash(_("بيانات الدخول غير صحيحة"), "danger")
            return redirect("/shop/login")

        if user.status == "blocked":
            flash(_("حسابك موقوف. تواصل معنا."), "danger")
            return redirect("/shop/login")

        # ✅ session خاص بالـ shop فقط
        session["shop_user_id"] = user.id

        # ✅ Auto-claim coupons (Atomic - SQLite friendly)
        now = datetime.utcnow()

        auto_coupons = (
            Coupon.query
            .filter(
                Coupon.auto_claim.is_(True),
                Coupon.is_active.is_(True),
            )
            .filter((Coupon.start_at == None) | (Coupon.start_at <= now))
            .filter((Coupon.end_at == None) | (Coupon.end_at >= now))
            .order_by(Coupon.id.desc())
            .all()
        )

        claimed_code = None

        for c in auto_coupons:
            # إذا انتهى العدد مسبقاً، تخطّاه
            if c.usage_limit is not None and int(c.usage_count or 0) >= int(c.usage_limit):
                continue

            # إذا أخذه من قبل، تخطّاه
            already = UserCoupon.query.filter_by(user_id=user.id, coupon_id=c.id).first()
            if already:
                continue

            try:
                # 1) أضف UserCoupon + flush لضرب unique constraint مبكّرًا
                db.session.add(UserCoupon(user_id=user.id, coupon_id=c.id))
                db.session.flush()

                # 2) زِد usage_count بشكل ذرّي (ما يتجاوز limit)
                if c.usage_limit is not None:
                    updated = (
                        db.session.query(Coupon)
                        .filter(Coupon.id == c.id, Coupon.usage_count < Coupon.usage_limit)
                        .update({Coupon.usage_count: Coupon.usage_count + 1}, synchronize_session=False)
                    )
                    if updated == 0:
                        # خلص العدد بنفس اللحظة
                        db.session.rollback()
                        continue
                else:
                    # غير محدود: زِد للإحصائيات
                    c.usage_count = int(c.usage_count or 0) + 1

                db.session.commit()
                claimed_code = c.code
                break

            except Exception:
                db.session.rollback()
                continue

        if claimed_code:
            flash(_("🎁 مبروك! حصلت على كوبون جديد: ") + claimed_code, "success")

        flash(_("تم تسجيل الدخول بنجاح ✅"), "success")
        return redirect("/shop/")

    # ------------------- REGISTER -------------------
    @app.get("/shop/register")
    def shop_register_view():
        return render_template("shop/register.html")

    @app.post("/shop/register")
    def shop_register_post():
        # بيانات الحساب
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        # بيانات شخصية
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        address = (request.form.get("address") or "").strip()

        if not email or not password or not password2:
            flash(_("يرجى تعبئة جميع الحقول المطلوبة"), "danger")
            return redirect("/shop/register")

        if password != password2:
            flash(_("كلمتا المرور غير متطابقتين"), "danger")
            return redirect("/shop/register")

        exists = User.query.filter_by(email=email).first()
        if exists:
            flash(_("هذا البريد مستخدم مسبقًا"), "warning")
            return redirect("/shop/register")

        user = User(
            email=email,
            role="buyer",
            status="pending",
            first_name=first_name or None,
            last_name=last_name or None,
            phone=phone or None,
            address=address or None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(_("تم إنشاء الحساب. حسابك قيد المراجعة الآن ✅"), "success")
        return redirect("/shop/login")

    # ------------------- LOGOUT -------------------
    @app.get("/shop/logout")
    def shop_logout():
        session.pop("shop_user_id", None)
        flash(_("تم تسجيل الخروج"), "info")
        return redirect("/shop/")

    # ------------------- ACCOUNT -------------------
