from datetime import datetime
from flask import render_template, session
from models import Coupon, UserCoupon, db
from .helpers import shop_active_or_admin_required  # عندك جاهز

def register(app):

    @app.get("/shop/coupons")
    @shop_active_or_admin_required
    def shop_coupons(user):
        now = datetime.utcnow()

        # كوبونات شغالة (للعرض)
        active = Coupon.query.order_by(Coupon.id.desc()).all()
        active = [c for c in active if c.is_running_now(now)]

        # كوبونات المستخدم (claimed)
        my = (
            UserCoupon.query
            .filter_by(user_id=user.id)
            .order_by(UserCoupon.id.desc())
            .all()
        )

        return render_template("shop/coupons.html", user=user, active=active, my=my, now=now)