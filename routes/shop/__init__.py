# routes/shop/__init__.py
from . import home, products, auth, account, ledger, offers, special_offers, about, contact, coupons


def register_shop_routes(app):
    """Register all shop routes on the given Flask app."""
    home.register(app)
    products.register(app)
    auth.register(app)
    account.register(app)
    ledger.register(app)
    offers.register(app)
    special_offers.register(app)
    about.register(app)
    contact.register(app)
    coupons.register(app)