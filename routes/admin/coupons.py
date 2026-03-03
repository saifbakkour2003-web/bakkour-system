# routes/admin/coupons.py
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_babel import gettext as _

from models import db, Coupon, User, UserCoupon
from utils.admin_auth import admin_required

admin_coupons_bp = Blueprint("admin_coupons", __name__, url_prefix="/admin/coupons")


def _parse_dt(v: str):
    v = (v or "").strip()
    if not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M")
    except Exception:
        return None


@admin_coupons_bp.get("/")
@admin_required
def list_coupons():
    coupons = Coupon.query.order_by(Coupon.id.desc()).all()
    return render_template("admin/coupons_list.html", coupons=coupons)


@admin_coupons_bp.get("/new")
@admin_required
def new_coupon():
    return render_template("admin/coupon_form.html", c=None)


@admin_coupons_bp.post("/new")
@admin_required
def create_coupon():
    code = (request.form.get("code") or "").strip().upper()
    title = (request.form.get("title") or "").strip() or None
    desc = (request.form.get("description") or "").strip() or None

    discount_amount = float(request.form.get("discount_amount") or 0)

    usage_limit = request.form.get("usage_limit")
    usage_limit = int(usage_limit) if usage_limit and usage_limit.isdigit() else None

    start_at = _parse_dt(request.form.get("start_at"))
    end_at = _parse_dt(request.form.get("end_at"))

    is_active = bool(request.form.get("is_active"))
    auto_claim = bool(request.form.get("auto_claim"))

    if not code:
        flash(_("يرجى إدخال كود الكوبون"), "danger")
        return redirect("/admin/coupons/new")

    exists = Coupon.query.filter_by(code=code).first()
    if exists:
        flash(_("هذا الكود مستخدم مسبقًا"), "danger")
        return redirect("/admin/coupons/new")

    c = Coupon(
        code=code,
        title=title,
        description=desc,
        discount_amount=discount_amount,
        usage_limit=usage_limit,
        start_at=start_at,
        end_at=end_at,
        is_active=is_active,
        auto_claim=auto_claim,
    )
    db.session.add(c)
    db.session.commit()

    flash(_("تم إنشاء الكوبون ✅"), "success")
    return redirect("/admin/coupons/")


@admin_coupons_bp.get("/<int:cid>/edit")
@admin_required
def edit_coupon(cid):
    c = Coupon.query.get_or_404(cid)
    return render_template("admin/coupon_form.html", c=c)


@admin_coupons_bp.post("/<int:cid>/edit")
@admin_required
def update_coupon(cid):
    c = Coupon.query.get_or_404(cid)

    c.code = (request.form.get("code") or "").strip().upper()
    c.title = (request.form.get("title") or "").strip() or None
    c.description = (request.form.get("description") or "").strip() or None
    c.discount_amount = float(request.form.get("discount_amount") or 0)

    usage_limit = request.form.get("usage_limit")
    c.usage_limit = int(usage_limit) if usage_limit and usage_limit.isdigit() else None

    c.start_at = _parse_dt(request.form.get("start_at"))
    c.end_at = _parse_dt(request.form.get("end_at"))

    c.is_active = bool(request.form.get("is_active"))
    c.auto_claim = bool(request.form.get("auto_claim"))

    db.session.commit()
    flash(_("تم حفظ التعديلات ✅"), "success")
    return redirect("/admin/coupons/")


@admin_coupons_bp.post("/<int:cid>/toggle")
@admin_required
def toggle_coupon(cid):
    c = Coupon.query.get_or_404(cid)
    c.is_active = not bool(c.is_active)
    db.session.commit()
    flash(_("تم تحديث حالة الكوبون"), "info")
    return redirect("/admin/coupons/")


# ✅ جديد: صفحة تعرض مين أخد هالكوبون
@admin_coupons_bp.get("/<int:cid>/claims")
@admin_required
def coupon_claims(cid):
    c = Coupon.query.get_or_404(cid)

    claims = (
        UserCoupon.query
        .join(User, User.id == UserCoupon.user_id)
        .filter(UserCoupon.coupon_id == c.id)
        .order_by(UserCoupon.claimed_at.desc(), UserCoupon.id.desc())
        .all()
    )

    return render_template("admin/coupon_claims.html", c=c, claims=claims)


# ✅ اختياري (مفيد): رجّع عداد الاستخدام للصفر + حذف كل المستلمين
@admin_coupons_bp.post("/<int:cid>/reset-claims")
@admin_required
def reset_coupon_claims(cid):
    c = Coupon.query.get_or_404(cid)

    # احذف العلاقات (مين أخده)
    UserCoupon.query.filter_by(coupon_id=c.id).delete(synchronize_session=False)

    # صفّر عداد الاستخدام
    c.usage_count = 0
    db.session.commit()

    flash(_("تم تصفير مستلمي الكوبون وعداد الاستخدام ✅"), "success")
    return redirect(url_for("admin_coupons.coupon_claims", cid=c.id))