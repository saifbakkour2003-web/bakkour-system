import sqlite3

DB_PATH = "instance/database.db"

con = sqlite3.connect(DB_PATH, timeout=30)
cur = con.cursor()

# تحديث department حسب main_category
cur.execute("""
UPDATE sub_category
SET department = (
    SELECT department
    FROM main_category
    WHERE main_category.id = sub_category.main_category_id
)
""")

con.commit()

rows = cur.execute(
    "SELECT id, name, main_category_id, department FROM sub_category ORDER BY id"
).fetchall()

con.close()

print("✅ Updated sub_category.department:")
for r in rows:
    print(r)
