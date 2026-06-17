"""Extract all 122 okooo companies across 5 pages."""
import sys, json, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"
cookies = [{"name": n, "value": v, "domain": ".okooo.com", "path": "/"} for pair in COOKIE.split("; ") if "=" in pair for n, v in [pair.split("=", 1)]]

all_companies = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    ctx.add_cookies(cookies)

    for pg in range(0, 5):
        page = ctx.new_page()
        url = f"https://www.okooo.com/soccer/match/1315851/odds/ajax/?page={pg}&trnum=0&companytype=BaijiaBooks"
        resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
        html = resp.body().decode("utf-8", errors="replace")

        # Extract CID + name from data-pname
        for m in re.finditer(r'<tr\s+id="tr(\d+)"[^>]*data-pname="([^"]*)"', html):
            cid = m.group(1)
            raw_name = m.group(2)
            clean_name = re.sub(r"<span[^>]*style='font-size:0;'[^>]*>[^<]*</span>", "", raw_name)
            all_companies[cid] = {"name": clean_name}

        # Extract country from each tr block
        for m in re.finditer(r'<tr\s+id="tr(\d+)".*?</tr>', html, re.DOTALL):
            cid = m.group(1)
            cm = re.search(r'<div class="countryname">([^<]+)</div>', m.group(0))
            if cm and cid in all_companies:
                all_companies[cid]["country"] = cm.group(1)

        page_count = len(re.findall(r'<tr\s+id="tr\d+"', html))
        print(f"  page {pg}: +{page_count} companies, running total={len(all_companies)}")
        page.close()
        time.sleep(2)

    browser.close()

# Print all
print(f"\n{'='*60}")
print(f"Total okooo companies: {len(all_companies)}")
print(f"{'='*60}")
for cid in sorted(all_companies.keys(), key=lambda x: int(x)):
    info = all_companies[cid]
    country = info.get("country", "")
    print(f"  CID {cid:>5} = {info['name']} ({country})")

# Save
with open(r"D:\Desktop\world cup\okooo_cid_all.json", "w", encoding="utf-8") as f:
    json.dump(all_companies, f, ensure_ascii=False, indent=2)
print(f"\nSaved to okooo_cid_all.json")
