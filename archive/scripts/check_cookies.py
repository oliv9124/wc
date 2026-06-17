import sqlite3
conn = sqlite3.connect("D:/Desktop/world cup/_cookies_tmp.db")
cur = conn.cursor()
cur.execute("SELECT DISTINCT host_key FROM cookies WHERE host_key LIKE '%okooo%'")
rows = cur.fetchall()
print(f"Okooo cookies in Profile 1: {len(rows)}")
for r in rows:
    print(f"  {r[0]}")
cur.execute("SELECT COUNT(*) FROM cookies")
print(f"Total cookies: {cur.fetchone()[0]}")
cur.execute("SELECT DISTINCT host_key FROM cookies LIMIT 20")
print("Sample hosts:")
for r in cur.fetchall():
    print(f"  {r[0]}")
conn.close()
