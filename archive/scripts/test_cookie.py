import os, sqlite3, json, base64
from pathlib import Path

cookie_db = Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies"
print(f"Cookie DB exists: {cookie_db.exists()}, size: {cookie_db.stat().st_size}")

try:
    conn = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT name, host_key, length(encrypted_value) FROM cookies WHERE host_key LIKE '%okooo%'")
    rows = cur.fetchall()
    print(f"Found {len(rows)} okooo cookies:")
    for name, host, evlen in rows:
        print(f"  {name} ({host}) encrypted_len={evlen}")
    conn.close()
except Exception as e:
    print(f"Direct read error: {e}")

    try:
        tmp = Path("D:/Desktop/world cup/_cookies_tmp.db")
        os.system(f'copy /Y "{cookie_db}" "{tmp}" >nul 2>&1')
        if tmp.exists():
            print(f"Copy succeeded, size={tmp.stat().st_size}")
            conn = sqlite3.connect(str(tmp))
            cur = conn.cursor()
            cur.execute("SELECT name, host_key FROM cookies WHERE host_key LIKE '%okooo%'")
            for r in cur.fetchall():
                print(f"  {r[0]} ({r[1]})")
            conn.close()
        else:
            print("Copy failed too")
    except Exception as e2:
        print(f"Copy method error: {e2}")
