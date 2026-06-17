"""Extract okooo CID mapping - UTF-8 decoding."""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"
cookies = [{"name": n, "value": v, "domain": ".okooo.com", "path": "/"} for pair in COOKIE.split("; ") if "=" in pair for n, v in [pair.split("=", 1)]]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    ctx.add_cookies(cookies)
    page = ctx.new_page()
    resp = page.goto(
        "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype=BaijiaBooks",
        wait_until="domcontentloaded", timeout=15000,
    )
    html = resp.body().decode("utf-8", errors="replace")

    # Parse <tr id="tr{cid}" ... data-pname="...">
    pattern = r'<tr\s+id="tr(\d+)"[^>]*data-pname="([^"]*)"'
    mapping = {}
    for m in re.finditer(pattern, html):
        cid = m.group(1)
        raw_name = m.group(2)
        clean_name = re.sub(r"<span[^>]*style='font-size:0;'[^>]*>[^<]*</span>", "", raw_name)
        mapping[cid] = clean_name

    # Extract country
    tr_pattern = r'<tr\s+id="tr(\d+)".*?</tr>'
    country_map = {}
    for m in re.finditer(tr_pattern, html, re.DOTALL):
        cid = m.group(1)
        cm = re.search(r'<div class="countryname">([^<]+)</div>', m.group(0))
        if cm:
            country_map[cid] = cm.group(1)

    result = {}
    for cid in sorted(mapping.keys(), key=lambda x: int(x)):
        name = mapping[cid]
        country = country_map.get(cid, "")
        result[cid] = {"name": name, "country": country}
        print(f"  CID {cid:>5} = {name} ({country})")

    with open(r"D:\Desktop\world cup\okooo_cid_mapping.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nTotal: {len(result)} companies saved to okooo_cid_mapping.json")

    page.close()
    browser.close()
