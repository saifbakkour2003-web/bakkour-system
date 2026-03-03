# routes/shop/home.py
from flask import render_template, session
from datetime import datetime
from models import Product, SubCategory, SpecialOffer
from utils.product_fetch import get_products_query
import random


def register(app):
    @app.get("/shop/")
    def shop_home():
        now = datetime.utcnow()

        base_q = (
            get_products_query(for_shop=True)
            .filter(
                Product.is_discounted == True,
                Product.discount_price.isnot(None),
                (Product.discount_start == None) | (Product.discount_start <= now),
                (Product.discount_end == None) | (Product.discount_end >= now),
            )
        )

        active_deals = (
            base_q
            .order_by(Product.discount_end.asc().nullslast(), Product.id.desc())
            .limit(8)   # خليهم 8 لأن الصفحة فيها grids حلوة
            .all()
        )

        upcoming_deals = (
            get_products_query(for_shop=True)
            .filter(
                Product.is_discounted == True,
                Product.discount_price.isnot(None),
                Product.discount_start.isnot(None),
                Product.discount_start > now,
            )
            .order_by(Product.discount_start.asc(), Product.id.desc())
            .limit(8)
            .all()
        )

        # مبدئياً فاضيين، منركّبهم لاحقاً
        best_sellers = []
        featured = []

        # =============================
        # Daily random 6 subcategories
        # (يتغيروا مرة باليوم)
        # =============================
        all_subs = SubCategory.query.order_by(SubCategory.id.asc()).all()

        daily_subs = []
        if all_subs:
            # Seed ثابت لليوم (حسب UTC)
            seed_str = now.strftime("%Y-%m-%d")
            rnd = random.Random(seed_str)

            # خلط ثابت لليوم + أخذ 6
            subs_copy = list(all_subs)
            rnd.shuffle(subs_copy)
            daily_subs = subs_copy[:6]

        # =============================
        # Daily random 10 products
        # (يتغيروا مرة باليوم)
        # =============================
        all_products = (
            get_products_query(for_shop=True)
            .order_by(Product.id.asc())
            .all()
        )

        daily_products = []
        if all_products:
            seed_str = now.strftime("%Y-%m-%d")
            rnd = random.Random("products-" + seed_str)

            prods_copy = list(all_products)
            rnd.shuffle(prods_copy)
            daily_products = prods_copy[:10]

        # =============================
        # Weekly offers (خصومات فعالة حالياً)
        # =============================
        weekly_offers = (
            get_products_query(for_shop=True)
            .filter(
                Product.is_discounted == True,
                Product.discount_price.isnot(None),
                Product.discount_start <= now,
                Product.discount_end >= now
            )
            .order_by(Product.discount_start.desc())
            .limit(12)
            .all()
        )
        now = datetime.utcnow()

        from models import SpecialOffer

        special_running = SpecialOffer.query.order_by(SpecialOffer.id.desc()).all()
        special_running = [o for o in special_running if o.is_running]




        return render_template(
            "shop/home.html",
            active_deals=active_deals,
            upcoming_deals=upcoming_deals,
            best_sellers=best_sellers,
            daily_subs=daily_subs,
            daily_products=daily_products,
            weekly_offers=weekly_offers,
            special_running=special_running,
            featured=featured,
            now=now,
        )