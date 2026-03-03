# routes/shop/offers.py
from datetime import datetime

from flask import render_template, request
from models import Product
from utils.product_fetch import get_products_query


def register(app):
    @app.get("/shop/offers")
    def shop_offers():
        now = datetime.utcnow()

        # عروض فعالة الآن (ضمن الفترة)
        query = (
            get_products_query(for_shop=True)
            .filter(
                Product.is_discounted == True,
                Product.discount_price.isnot(None),
                (Product.discount_start == None) | (Product.discount_start <= now),
                (Product.discount_end == None) | (Product.discount_end >= now),
            )
        )

        # ترتيب: اللي قرب يخلص أولاً، بعدين الأحدث
        products = (
            query
            .order_by(Product.discount_end.asc().nullslast(), Product.id.desc())
            .all()
        )

        return render_template("shop/offers.html", products=products, now=now)