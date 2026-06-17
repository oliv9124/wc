"""Scan okooo odds AJAX pagination to find all companies."""
import sys, json, re, time
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

    all_companies = {}

    for pg in range(0, 5):
        page = ctx.new_page()
        url = f"https://www.okooo.com/soccer/match/1315851/odds/ajax/?page={pg}&trnum=0&companytype=BaijiaBooks"
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            html = resp.body().decode("utf-8", errors="replace")
            matches = re.findall(r'<tr\s+id="tr(\d+)"[^>]*data-pname="([^"]*)"', html)
            print(f"  page={pg}: {len(matches)} companies, html={len(html)}")
            for cid, name in matches:
                clean = re.sub(r"<span[^>]*style='font-size:0;'[^>]*>[^<]*</span>", "", name)
                all_companies[cid] = clean
        except Exception as e:
            print(f"  page={pg}: ERROR {e}")
        page.close()
        time.sleep(2)

    # Also try trnum variations
    print("\nTrying trnum variations...")
    for trnum in [1, 2, 30, 100]:
        page = ctx.new_page()
        url = f"https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum={trnum}&companytype=BaijiaBooks"
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            html = resp.body().decode("utf-8", errors="replace")
            count = len(re.findall(r'<tr\s+id="tr\d+"', html))
            print(f"  trnum={trnum}: {count} companies, html={len(html)}")
        except Exception as e:
            print(f"  trnum={trnum}: ERROR {e}")
        page.close()
        time.sleep(2)

    # Try the full page (not AJAX) to see total company count
    print("\nFetching full odds page...")
    page = ctx.new_page()
    resp = page.goto(
        "https://www.okooo.com/soccer/match/1315851/odds/",
        wait_until="domcontentloaded", timeout=20000,
    )
    html = resp.body().decode("utf-8", errors="replace")
    # Check for company count indicators
    total_tr = len(re.findall(r'<tr\s+id="tr\d+"', html))
    # Look for pagination or total count
    count_match = re.search(r'(\d+)\s*家', html)
    print(f"  Full page: html={len(html)}, tr count={total_tr}")
    if count_match:
        print(f"  Page says: {count_match.group(0)}")

    # Check for JS that loads additional companies
    js_urls = re.findall(r'(odds/ajax/\?[^"\']+)', html)
    print(f"  AJAX URLs in page: {js_urls[:5]}")

    page.close()
    browser.close()

print(f"\nTotal unique companies found: {len(all_companies)}")
