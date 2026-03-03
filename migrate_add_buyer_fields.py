import sqlite3

DB_PATH = "instance/database.db"  # حسب اللي عندك محفوظ بالذاكرة

def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cur.fetchall()]  # row[1] = column name
    return column in cols

def add_column(cur, table, column, col_type):
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    table = "user"  # انتبه: اسم الجدول قد يكون users أو user حسب موديلك

    # تأكد اسم الجدول الحقيقي
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)

    # إذا جدولك اسمه "users" بدل "user" عدّل السطر فوق
    if table not in tables:
        if "users" in tables:
            table = "users"
        else:
            raise Exception("لم أجد جدول user ولا users. عدّل اسم الجدول حسب مشروعك.")

    additions = [
        ("first_name", "VARCHAR(120)"),
        ("last_name",  "VARCHAR(120)"),
        ("phone",      "VARCHAR(50)"),
        ("address",    "VARCHAR(255)"),
    ]

    for col, typ in additions:
        if column_exists(cur, table, col):
            print(f"OK: {col} already exists")
        else:
            print(f"Adding: {col} ...")
            add_column(cur, table, col, typ)

    conn.commit()
    conn.close()
    print("Done ✅")

if __name__ == "__main__":
    main()