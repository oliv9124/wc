"""Collect okooo change history data using Chrome cookies."""
import json, os, sys, shutil, sqlite3, base64, re, time, struct
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "okooo" / "changes_v2"
DATA.mkdir(parents=True, exist_ok=True)

# ── Chrome cookie decryption (Windows DPAPI + AES-GCM) ──
def get_chrome_key():
    local_state_path = Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data" / "Local State"
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]  # Remove DPAPI prefix
    import win32crypt
    return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

def decrypt_cookie(encrypted_value, key):
    if encrypted_value[:3] == b'v10' or encrypted_value[:3] == b'v20':
        from Crypto.Cipher import AES
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:-16]
        tag = encrypted_value[-16:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
    else:
        import win32crypt
        return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode('utf-8')

def get_okooo_cookies():
    key = get_chrome_key()
    cookie_db = Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies"
    tmp_db = ROOT / "_cookies_tmp.db"
    # Try multiple copy methods to handle Chrome lock
    try:
        shutil.copy2(cookie_db, tmp_db)
    except PermissionError:
        os.system(f'copy /Y "{cookie_db}" "{tmp_db}" >nul 2>&1')
        if not tmp_db.exists():
            # Try robocopy as last resort
            os.system(f'robocopy "{cookie_db.parent}" "{tmp_db.parent}" "{cookie_db.name}" /NFL /NDL /NJH /NJS >nul 2>&1')
            if (tmp_db.parent / cookie_db.name).exists():
                (tmp_db.parent / cookie_db.name).rename(tmp_db)

    if not tmp_db.exists() or tmp_db.stat().st_size == 0:
        # Direct read-only connection as fallback
        conn = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(str(tmp_db))

    if not tmp_db.exists():
        conn = sqlite3.connect(f"file:{cookie_db}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(str(tmp_db))
    cursor = conn.cursor()
    cursor.execute("SELECT name, encrypted_value FROM cookies WHERE host_key LIKE '%okooo%'")
    cookies = {}
    for name, enc_val in cursor.fetchall():
        try:
            val = decrypt_cookie(enc_val, key)
            if val:
                cookies[name] = val
        except Exception:
            pass
    conn.close()
    tmp_db.unlink(missing_ok=True)
    return cookies

# ── HTML parser for change history tables ──
class ChangeTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_td = False
        self.rows = []
        self.current_row = []
        self.current_cell = ""

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_tr = True
            self.current_row = []
        elif tag == "td" and self.in_tr:
            self.in_td = True
            self.current_cell = ""

    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            self.in_td = False
            self.current_row.append(self.current_cell.strip())
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            if len(self.current_row) >= 5:
                self.rows.append(self.current_row)

    def handle_data(self, data):
        if self.in_td:
            self.current_cell += data

def parse_changes(html):
    parser = ChangeTableParser()
    parser.feed(html)
    results = []
    for row in parser.rows:
        w = row[2].strip() if len(row) > 2 else ""
        if w and re.search(r'[\d.]', w):
            results.append({
                "time": row[0].strip(),
                "w": w, "d": row[3].strip(), "l": row[4].strip(),
                "pw": row[5].strip() if len(row) > 5 else "",
                "pd": row[6].strip() if len(row) > 6 else "",
                "pl": row[7].strip() if len(row) > 7 else "",
                "kw": row[8].strip() if len(row) > 8 else "",
                "kd": row[9].strip() if len(row) > 9 else "",
                "kl": row[10].strip() if len(row) > 10 else "",
                "pay": row[11].strip() if len(row) > 11 else "",
            })
    return results

# ── Key companies to track ──
KEY_COMPANIES = [
    ("14", "威廉希尔"), ("82", "Bet365"), ("27", "立博"), ("25", "bwin"),
    ("84", "Coral"), ("49", "PaddyPower"), ("157", "Skybet"), ("50", "Pinnacle"),
    ("879", "BetfairExch"), ("560", "BetVictor"), ("65", "皇冠"),
    ("19", "必发"), ("43", "Interwetten"), ("94", "SNAI"),
    ("116", "易胜博"), ("245", "Betway"), ("538", "Marathon"), ("24", "99家平均"),
]

def fetch_change_history(mid, cid, cookie_str, retries=2):
    url = f"https://www.okooo.com/soccer/match/{mid}/odds/change/{cid}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": cookie_str,
        "Referer": f"https://www.okooo.com/soccer/match/{mid}/odds/",
        "Accept": "text/html,application/xhtml+xml",
    }
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=headers)
            resp = urlopen(req, timeout=15)
            raw = resp.read()
            html = raw.decode("gbk", errors="replace")
            if "captcha" in html.lower() or "WAF" in html:
                print(f"  ⚠ WAF block on cid={cid}, attempt {attempt+1}")
                time.sleep(2)
                continue
            if "登录" in html and "change" not in html:
                print(f"  ⚠ Login required for cid={cid}")
                return None
            return parse_changes(html)
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
            else:
                print(f"  ✗ Error cid={cid}: {e}")
                return None
    return None

def collect_match(mid, match_label, cookie_str):
    out_file = DATA / f"{mid}_eu_changes.json"
    if out_file.exists():
        existing = json.load(open(out_file, "r", encoding="utf-8"))
        if len(existing.get("companies", {})) >= 10:
            print(f"  ✓ Already collected ({len(existing['companies'])} companies)")
            return existing

    print(f"  Collecting {match_label} (mid={mid})...")
    companies = {}
    for cid, name in KEY_COMPANIES:
        changes = fetch_change_history(mid, cid, cookie_str)
        if changes:
            companies[cid] = {"name": name, "changes": changes}
            print(f"    {name}({cid}): {len(changes)} changes")
        time.sleep(0.3)

    result = {"mid": mid, "label": match_label, "companies": companies}
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"  → Saved {len(companies)} companies to {out_file.name}")
    return result

def main():
    print("Reading Chrome cookies for okooo.com...")
    cookies = get_okooo_cookies()
    if not cookies:
        print("✗ No okooo cookies found. Please login to okooo.com in Chrome first.")
        return

    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
    print(f"✓ Found {len(cookies)} cookies")

    # Test with one request
    print("Testing connection...")
    test = fetch_change_history("1315893", "82", cookie_str)
    if test is None:
        print("✗ Connection test failed. Cookies may be invalid.")
        return
    print(f"✓ Test OK: Bet365 has {len(test)} changes for match 1315893")

    # Load match config
    config = json.load(open(ROOT / "worldcup_fids.json", "r", encoding="utf-8"))

    total_companies = 0
    for m in config["matches"]:
        mid = m.get("ok_mid", "")
        if not mid:
            continue
        label = f"{m['home']}vs{m['away']}"
        result = collect_match(mid, label, cookie_str)
        total_companies += len(result.get("companies", {}))

    print(f"\n✓ Done! Collected data for {total_companies} company-match pairs")

if __name__ == "__main__":
    main()
