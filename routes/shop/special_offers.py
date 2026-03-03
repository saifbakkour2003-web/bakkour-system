from datetime import datetime
from flask import render_template
from sqlalchemy import or_, and_
from models import SpecialOffer

def register(app):

    @app.get("/shop/special-offers")
    def shop_special_offers():
        now = datetime.utcnow()

        base = SpecialOffer.query.order_by(SpecialOffer.id.desc())

        running = base.filter(
            SpecialOffer.is_archived.is_(False),
            SpecialOffer.is_active.is_(True),
            SpecialOffer.is_cancelled.is_(False),
            or_(SpecialOffer.start_at.is_(None), SpecialOffer.start_at <= now),
            or_(SpecialOffer.end_at.is_(None), SpecialOffer.end_at >= now),
        ).all()

        previous = base.filter(
            SpecialOffer.is_archived.is_(False),
            or_(
                SpecialOffer.is_active.is_(False),
                SpecialOffer.is_cancelled.is_(True),
                and_(SpecialOffer.end_at.isnot(None), SpecialOffer.end_at < now),
            )
        ).all()

        archived = base.filter(
            SpecialOffer.is_archived.is_(True)
        ).all()

        return render_template(
            "shop/special_offers.html",
            running=running,
            previous=previous,
            archived=archived,
            now=now
        )