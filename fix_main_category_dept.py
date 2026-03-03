import sqlite3

con = sqlite3.connect("instance/database.db")
cur = con.cursor()

cur.execute("UPDATE main_category SET department='electrical' WHERE id=1")
cur.execute("UPDATE main_category SET department='linens'     WHERE id=2")
cur.execute("UPDATE main_category SET department='crystal'    WHERE id=3")

con.commit()

rows = cur.execute("SELECT id, name, department FROM main_category").fetchall()
con.close()

print("✅ main_category departments:")
for r in rows:
    print(r)
