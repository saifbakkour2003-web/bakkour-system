from app import db, app
from sqlalchemy import text

with app.app_context():
    with db.engine.connect() as conn:
        # إضافة العمود ledger لو مش موجود
        try:
            conn.execute(text(
                "ALTER TABLE customer ADD COLUMN ledger VARCHAR(50) NOT NULL DEFAULT 'تقسيط';"
            ))
            print("تم إضافة العمود ledger")
        except Exception as e:
            print("العمود ledger موجود مسبقاً:", e)

        # إضافة العمود phone لو مش موجود
        try:
            conn.execute(text(
                "ALTER TABLE customer ADD COLUMN phone VARCHAR(20) DEFAULT '';"
            ))
            print("تم إضافة العمود phone")
        except Exception as e:
            print("العمود phone موجود مسبقاً:", e)

        # إضافة العمود initial_payment للمنتجات
        try:
            conn.execute(text(
                "ALTER TABLE installment_product ADD COLUMN initial_payment FLOAT DEFAULT 0.0;"
            ))
            print("تم إضافة العمود initial_payment")
        except Exception as e:
            print("العمود initial_payment موجود مسبقاً:", e)
