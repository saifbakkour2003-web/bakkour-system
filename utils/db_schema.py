import sqlite3
from flask import current_app
from extensions import db


def _sqlite_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    return any(r[1] == column for r in cur.fetchall())


def ensure_sqlite_column(table_name: str, column_name: str, column_sql: str) -> None:
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite:///"):
        return

    engine = db.get_engine()
    raw = engine.raw_connection()
    try:
        conn = raw.connection
        if not _sqlite_has_column(conn, table_name, column_name):
            conn.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql};"
            )
            conn.commit()
    finally:
        raw.close()


def patch_general_cash_payment():
    ensure_sqlite_column("general_cash_payment", "source", "TEXT DEFAULT 'دفعة عامة'")


def patch_sale_table_add_columns():
    ensure_sqlite_column("sale", "manual_name", "TEXT")
    ensure_sqlite_column("sale", "manual_code", "TEXT")


def rebuild_sale_table_allow_null_product_id():
    """
    SQLite لا يدعم تغيير NOT NULL إلى NULL بسهولة.
    لذلك نعيد بناء جدول sale مع:
    - product_id يصبح NULLABLE
    - إضافة manual_name/manual_code (إذا مش موجودين)
    بدون خسارة بيانات.
    """
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not uri.startswith("sqlite:///"):
        return

    engine = db.get_engine()
    raw = engine.raw_connection()
    try:
        conn = raw.connection

        # تأكد من وجود جدول sale
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sale';"
        )
        if not cur.fetchone():
            return

        # افحص product_id إذا كان NOT NULL
        info = conn.execute("PRAGMA table_info(sale);").fetchall()
        # row: (cid, name, type, notnull, dflt_value, pk)
        product_row = next((r for r in info if r[1] == "product_id"), None)
        if not product_row:
            return

        notnull = int(product_row[3] or 0)

        # إذا صار nullable سابقاً، ما في داعي rebuild
        # بس بدنا نضمن أعمدة اليدوي موجودة
        if notnull == 0:
            patch_sale_table_add_columns()
            return

        # ✅ ابدأ rebuild
        conn.execute("PRAGMA foreign_keys=OFF;")
        conn.execute("BEGIN;")

        # جدول جديد مؤقت
        conn.execute("""
            CREATE TABLE sale_new (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NULL,
                customer_id INTEGER NULL,
                sale_type VARCHAR(20) NOT NULL,
                sell_price FLOAT NOT NULL,
                cost_price FLOAT NOT NULL,
                manual_name VARCHAR(200),
                manual_code VARCHAR(60),
                date_created DATETIME,
                FOREIGN KEY(product_id) REFERENCES product(id),
                FOREIGN KEY(customer_id) REFERENCES customer(id)
            );
        """)

        # انسخ البيانات القديمة مع الحفاظ على الموجود
        # إذا الأعمدة اليدوية غير موجودة بالقديم، نحط NULL
        old_cols = [r[1] for r in info]

        has_manual_name = "manual_name" in old_cols
        has_manual_code = "manual_code" in old_cols

        select_manual_name = "manual_name" if has_manual_name else "NULL AS manual_name"
        select_manual_code = "manual_code" if has_manual_code else "NULL AS manual_code"

        conn.execute(f"""
            INSERT INTO sale_new (id, product_id, customer_id, sale_type, sell_price, cost_price, manual_name, manual_code, date_created)
            SELECT id, product_id, customer_id, sale_type, sell_price, cost_price, {select_manual_name}, {select_manual_code}, date_created
            FROM sale;
        """)

        conn.execute("DROP TABLE sale;")
        conn.execute("ALTER TABLE sale_new RENAME TO sale;")

        conn.execute("COMMIT;")
        conn.execute("PRAGMA foreign_keys=ON;")

    except Exception:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise
    finally:
        raw.close()


def apply_all_patches():
    patch_general_cash_payment()
    # إذا بدك بس columns بدون rebuild:
    # patch_sale_table_add_columns()
    # لكن نحن بدنا rebuild لأن product_id NOT NULL
    rebuild_sale_table_allow_null_product_id()