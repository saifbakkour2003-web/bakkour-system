import os
import sys

# ✅ خَلّي جذر المشروع ضمن sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from extensions import db
from models import Product

prefix_map = {"electrical": "E", "linens": "L", "crystal": "C"}

with app.app_context():
    products = Product.query.order_by(Product.id.asc()).all()
    updated = 0

    for p in products:
        if not p.serial_no:
            dept = p.department or "electrical"
            prefix = prefix_map.get(dept, "E")
            p.serial_no = f"{prefix}-{p.id:06d}"
            updated += 1

    db.session.commit()
    print(f"Updated serial_no for {updated} products.")
