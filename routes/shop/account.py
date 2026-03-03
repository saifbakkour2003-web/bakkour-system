# routes/shop/account.py
from datetime import datetime

from flask import render_template, flash, request, redirect
from flask_babel import gettext as _

from models import db, Customer, Coupon, UserCoupon
from .helpers import shop_active_or_admin_required, is_active_or_admin


def _clean_code(s: str) -> str:
    return (s or "").strip().upper().replace(" ", "")


def register(app):

    # ✅ لو حدا فتح /shop/account بالغلط، ودّيه على /shop/my
    @app.get("/shop/account")
    def shop_account_redirect():
        return redirect("/shop/my")

    # =========================
    # صفحة حسابي الأساسية
    # =========================
    @app.get("/shop/my")
    @shop_active_or_admin_required
    def shop_my(user):
        # إذا مو active ولا admin: الصفحة تظهر بس بدون بيانات حساسة
        if not is_active_or_admin(user):
            flash(_("حسابك قيد المراجعة. الأسعار والصفحة الخاصة ستظهر بعد التفعيل."), "warning")
            return render_template(
                "shop/my.html",
                user=user,
                customer=None,
                my_coupons=[],
                now=datetime.utcnow(),
            )

        # ربط الدفتر
        customer = None
        if user.customer_ref_code:
            customer = Customer.query.filter_by(custom_id=user.customer_ref_code).first()

        # كوبونات المستخدم
        my_coupons = (
            UserCoupon.query
            .filter_by(user_id=user.id)
            .join(Coupon, Coupon.id == UserCoupon.coupon_id)
            .order_by(UserCoupon.claimed_at.desc(), UserCoupon.id.desc())
            .all()
        )

        return render_template(
            "shop/my.html",
            user=user,
            customer=customer,
            my_coupons=my_coupons,
            now=datetime.utcnow(),
        )

    # =========================
    # ✅ تحديث بيانات المستخدم (اسم/هاتف/عنوان)
    # =========================
    @app.post("/shop/my/update")
    @shop_active_or_admin_required
    def shop_my_update(user):
        # حتى لو pending خليه يقدر يعدّل معلوماته
        user.first_name = (request.form.get("first_name") or "").strip() or None
        user.last_name = (request.form.get("last_name") or "").strip() or None
        user.phone = (request.form.get("phone") or "").strip() or None
        user.address = (request.form.get("address") or "").strip() or None

        db.session.commit()
        flash(_("تم تحديث معلوماتك ✅"), "success")
        return redirect("/shop/my")

    # =========================
    # ✅ إدخال كوبون (انستا/واتس…)
    # =========================
    @app.post("/shop/my/coupons/claim")
    @shop_active_or_admin_required
    def shop_claim_coupon(user):
        if not is_active_or_admin(user):
            flash(_("حسابك قيد المراجعة. ستتمكن من استخدام الكوبونات بعد التفعيل."), "warning")
            return redirect("/shop/my")

        code = _clean_code(request.form.get("code"))
        if not code:
            flash(_("اكتب كود الكوبون أولاً."), "danger")
            return redirect("/shop/my#coupons")

        now = datetime.utcnow()
        c = Coupon.query.filter_by(code=code).first()
        if not c:
            flash(_("هذا الكوبون غير موجود."), "danger")
            return redirect("/shop/my#coupons")

        # تحقق تشغيل الكوبون (active + وقت + limit)
        if not c.is_running_now(now):
            if (c.usage_limit is not None) and (int(c.usage_count or 0) >= int(c.usage_limit)):
                flash(_("انتهت كمية هذا الكوبون (خلص العدد)."), "warning")
            elif c.start_at and now < c.start_at:
                flash(_("هذا الكوبون لم يبدأ بعد."), "warning")
            elif c.end_at and now > c.end_at:
                flash(_("انتهت صلاحية هذا الكوبون."), "warning")
            else:
                flash(_("هذا الكوبون غير متاح حالياً."), "warning")
            return redirect("/shop/my#coupons")

        # هل أخذه من قبل؟
        already = UserCoupon.query.filter_by(user_id=user.id, coupon_id=c.id).first()
        if already:
            flash(_("أنت حاصل على هذا الكوبون مسبقاً ✅"), "info")
            return redirect("/shop/my#coupons")

        # ✅ Atomic claim (SQLite-friendly)
        try:
            uc = UserCoupon(user_id=user.id, coupon_id=c.id)
            db.session.add(uc)
            db.session.flush()  # unique constraint check

            if c.usage_limit is not None:
                updated = (
                    db.session.query(Coupon)
                    .filter(Coupon.id == c.id, Coupon.usage_count < Coupon.usage_limit)
                    .update({Coupon.usage_count: Coupon.usage_count + 1}, synchronize_session=False)
                )
                if updated == 0:
                    db.session.rollback()
                    flash(_("انتهت كمية هذا الكوبون (خلص العدد)."), "warning")
                    return redirect("/shop/my#coupons")
            else:
                c.usage_count = int(c.usage_count or 0) + 1

            db.session.commit()

        except Exception:
            db.session.rollback()
            flash(_("صار خطأ أثناء إضافة الكوبون. جرّب مرة ثانية."), "danger")
            return redirect("/shop/my#coupons")

        flash(_("تم إضافة الكوبون لحسابك ✅ ") + f"({c.code})", "success")
        return redirect("/shop/my#coupons")