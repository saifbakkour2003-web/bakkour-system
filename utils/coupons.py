# utils/coupons.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import and_
from models import db, Coupon, UserCoupon


def utcnow() -> datetime:
    return datetime.utcnow()


def is_coupon_running(c: Coupon, now: Optional[datetime] = None) -> bool:
    """
    كوبون شغّال الآن؟
    يعتمد على: is_active + start_at/end_at + usage_limit
    """
    now = now or utcnow()

    if not c:
        return False

    if not bool(getattr(c, "is_active", False)):
        return False

    # usage_limit check
    usage_limit = getattr(c, "usage_limit", None)
    usage_count = int(getattr(c, "usage_count", 0) or 0)
    if usage_limit is not None and usage_count >= int(usage_limit):
        return False

    start_at = getattr(c, "start_at", None)
    end_at = getattr(c, "end_at", None)

    if start_at and now < start_at:
        return False
    if end_at and now > end_at:
        return False

    return True


def user_already_claimed(user_id: int, coupon_id: int) -> bool:
    return (
        db.session.query(UserCoupon.id)
        .filter_by(user_id=user_id, coupon_id=coupon_id)
        .first()
        is not None
    )


def claim_coupon_for_user(
    *,
    user_id: int,
    coupon: Coupon,
    now: Optional[datetime] = None,
) -> Tuple[bool, str]:
    """
    يحاول يعطي الكوبون للمستخدم.
    يرجّع: (ok, message)

    - يمنع تكرار نفس الكوبون لنفس المستخدم
    - يمنع تجاوز usage_limit
    - يزيد usage_count
    """
    now = now or utcnow()

    if not coupon:
        return False, "الكوبون غير موجود"

    if not is_coupon_running(coupon, now=now):
        # هنا السبب ممكن يكون انتهى/لسا ما بدأ/غير مفعل/خلص العدد
        if not coupon.is_active:
            return False, "الكوبون غير مفعل"
        if coupon.start_at and now < coupon.start_at:
            return False, "الكوبون لم يبدأ بعد"
        if coupon.end_at and now > coupon.end_at:
            return False, "الكوبون منتهي"
        if coupon.usage_limit is not None and (coupon.usage_count or 0) >= coupon.usage_limit:
            return False, "هذا الكوبون وصل للحد الأقصى"
        return False, "لا يمكن استخدام الكوبون الآن"

    # already claimed
    if user_already_claimed(user_id, coupon.id):
        return False, "أنت حاصل على هذا الكوبون مسبقًا"

    # ✅ حاول بطريقة آمنة قدر الإمكان مع SQLite
    # ملاحظة: SQLite ما يدعم SELECT ... FOR UPDATE بشكل فعلي مثل PostgreSQL،
    # بس منعمل check + increment + commit بسرعة لتقليل احتمالية السباق.
    usage_limit = coupon.usage_limit
    usage_count = int(coupon.usage_count or 0)

    if usage_limit is not None and usage_count >= int(usage_limit):
        return False, "هذا الكوبون وصل للحد الأقصى"

    try:
        # add link
        db.session.add(UserCoupon(user_id=user_id, coupon_id=coupon.id))

        # increment usage_count
        coupon.usage_count = usage_count + 1

        db.session.commit()
        return True, "تم الحصول على الكوبون ✅"
    except Exception:
        db.session.rollback()
        # ممكن يصير UniqueConstraint لو بنفس اللحظة انعمل claim مرتين
        return False, "تعذر الحصول على الكوبون (قد يكون تم أخذه بالفعل)"


def claim_coupon_by_code_for_user(
    *,
    user_id: int,
    code: str,
    now: Optional[datetime] = None,
) -> Tuple[bool, str, Optional[Coupon]]:
    """
    Manual claim: المستخدم يكتب الكود.
    """
    now = now or utcnow()
    code = (code or "").strip().upper()
    if not code:
        return False, "أدخل كود الكوبون", None

    coupon = Coupon.query.filter(Coupon.code.ilike(code)).first()
    if not coupon:
        return False, "كود الكوبون غير صحيح", None

    ok, msg = claim_coupon_for_user(user_id=user_id, coupon=coupon, now=now)
    return ok, msg, coupon


def auto_claim_first_available(
    *,
    user_id: int,
    now: Optional[datetime] = None,
) -> Tuple[bool, Optional[Coupon], str]:
    """
    Auto-claim: عند تسجيل الدخول
    ياخد أول كوبون auto_claim شغّال ومتوفر وما أخده المستخدم من قبل.
    """
    now = now or utcnow()

    # جيب كل auto_claim الفعالة
    autos = (
        Coupon.query
        .filter(
            Coupon.auto_claim.is_(True),
            Coupon.is_active.is_(True),
        )
        .order_by(Coupon.id.desc())
        .all()
    )

    for c in autos:
        if not is_coupon_running(c, now=now):
            continue

        if user_already_claimed(user_id, c.id):
            continue

        ok, msg = claim_coupon_for_user(user_id=user_id, coupon=c, now=now)
        if ok:
            return True, c, msg
        # إذا فشل بسبب limit/سباق، جرّب اللي بعده
        continue

    return False, None, "لا يوجد كوبون تلقائي متاح الآن"