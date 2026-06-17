"""Scan all companies from both sites."""
import sys, json, re, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"

cookies = [{"name": n, "value": v, "domain": ".okooo.com", "path": "/"} for pair in COOKIE.split("; ") if "=" in pair for n, v in [pair.split("=", 1)]]

# ============================================================
# Part 1: okooo - try different companytype values
# ============================================================
print("=" * 60)
print("okooo: testing different companytype params")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    ctx.add_cookies(cookies)

    # Try: no companytype, AllBooks, all, empty
    test_urls = [
        ("no param", "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0"),
        ("AllBooks", "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype=AllBooks"),
        ("empty", "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype="),
        ("BaijiaBooks", "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype=BaijiaBooks"),
    ]

    for label, url in test_urls:
        page = ctx.new_page()
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            raw = resp.body()
            html = raw.decode("utf-8", errors="replace")
            tr_count = len(re.findall(r'<tr\s+id="tr\d+"', html))
            print(f"  [{label}] status={resp.status}, html={len(html)}, companies={tr_count}")
        except Exception as e:
            print(f"  [{label}] ERROR: {e}")
        page.close()
        time.sleep(2)

    # Now fetch the one with most companies and extract all CIDs
    print("\nFetching full company list...")
    page = ctx.new_page()
    resp = page.goto(
        "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0",
        wait_until="domcontentloaded", timeout=15000,
    )
    html = resp.body().decode("utf-8", errors="replace")

    pattern = r'<tr\s+id="tr(\d+)"[^>]*data-pname="([^"]*)"'
    okooo_all = {}
    for m in re.finditer(pattern, html):
        cid = m.group(1)
        raw_name = m.group(2)
        clean_name = re.sub(r"<span[^>]*style='font-size:0;'[^>]*>[^<]*</span>", "", raw_name)
        okooo_all[cid] = clean_name

    # Extract country
    tr_blocks = re.finditer(r'<tr\s+id="tr(\d+)".*?</tr>', html, re.DOTALL)
    country_map = {}
    for m in tr_blocks:
        cid = m.group(1)
        cm = re.search(r'<div class="countryname">([^<]+)</div>', m.group(0))
        if cm:
            country_map[cid] = cm.group(1)

    print(f"\nTotal okooo companies: {len(okooo_all)}")
    okooo_result = {}
    for cid in sorted(okooo_all.keys(), key=lambda x: int(x)):
        name = okooo_all[cid]
        country = country_map.get(cid, "")
        okooo_result[cid] = {"name": name, "country": country}
        print(f"  CID {cid:>5} = {name} ({country})")

    page.close()
    browser.close()

# Save
with open(r"D:\Desktop\world cup\okooo_cid_all.json", "w", encoding="utf-8") as f:
    json.dump(okooo_result, f, ensure_ascii=False, indent=2)
print(f"\nSaved {len(okooo_result)} okooo companies to okooo_cid_all.json")
