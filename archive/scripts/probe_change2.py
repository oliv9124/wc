"""Re-probe the odds/change page and also check for AJAX data loading."""
import sys, json, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent

cookie_str = (ROOT / "okooo_cookie.txt").read_text().strip()
cookies = []
for pair in cookie_str.split("; "):
    if "=" in pair:
        n, v = pair.split("=", 1)
        cookies.append({"name": n, "value": v, "domain": ".okooo.com", "path": "/"})

MID = "1315851"
CID = "27"  # Bet365

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    ctx.add_cookies(cookies)

    # 1. European odds change page
    print("=== /odds/change/{cid}/ ===")
    page = ctx.new_page()

    # Intercept network requests to catch AJAX calls
    ajax_urls = []
    def on_request(req):
        if "ajax" in req.url.lower() or "change" in req.url.lower() or "api" in req.url.lower():
            ajax_urls.append(req.url)
    page.on("request", on_request)

    url = f"https://www.okooo.com/soccer/match/{MID}/odds/change/{CID}/"
    resp = page.goto(url, wait_until="networkidle", timeout=30000)
    html = resp.body().decode("utf-8", errors="replace")
    print(f"Status: {resp.status}, Size: {len(html)}")

    with open(ROOT / "probe_change_odds.html", "w", encoding="utf-8") as f:
        f.write(html)

    if ajax_urls:
        print(f"Intercepted AJAX calls:")
        for u in ajax_urls:
            print(f"  {u}")

    # Look for odds data in HTML
    # Try finding data in script tags
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for i, s in enumerate(scripts):
        if re.search(r'[\d]+\.[\d]{2}', s) and len(s) > 100:
            print(f"\nScript {i} ({len(s)} chars) has decimal numbers")
            # Check for array/json data
            if '[' in s and ']' in s:
                print(f"  Has array data")
                print(f"  Preview: {s[:500]}")

    # Check for table with class related to odds
    odds_tables = re.findall(r'<table[^>]*class="[^"]*(?:odd|change|detail|list)[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
    print(f"\nOdds-related tables: {len(odds_tables)}")

    # Just look at ALL table content
    all_tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
    for i, t in enumerate(all_tables):
        trs = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL)
        if len(trs) > 3:
            print(f"\nTable {i} ({len(trs)} rows):")
            for j, tr in enumerate(trs[:4]):
                tds = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.DOTALL)
                clean = [re.sub(r'<[^>]+>', '', td).strip()[:20] for td in tds]
                print(f"  Row {j}: {clean}")

    page.close()

    # 2. Try /history/ page
    print("\n\n=== /history/ ===")
    page = ctx.new_page()
    ajax_urls2 = []
    def on_request2(req):
        if "ajax" in req.url.lower() or "history" in req.url.lower():
            ajax_urls2.append(req.url)
    page.on("request", on_request2)

    url2 = f"https://www.okooo.com/soccer/match/{MID}/history/"
    resp2 = page.goto(url2, wait_until="networkidle", timeout=30000)
    html2 = resp2.body().decode("utf-8", errors="replace")
    print(f"Status: {resp2.status}, Size: {len(html2)}")

    if ajax_urls2:
        print(f"AJAX calls:")
        for u in ajax_urls2:
            print(f"  {u}")

    # Check title
    title = re.search(r'<title>(.*?)</title>', html2)
    if title:
        print(f"Title: {title.group(1)}")

    clean2 = re.sub(r'<script[^>]*>.*?</script>', '', html2, flags=re.DOTALL)
    clean2 = re.sub(r'<style[^>]*>.*?</style>', '', clean2, flags=re.DOTALL)
    clean2 = re.sub(r'<[^>]+>', ' ', clean2)
    clean2 = re.sub(r'\s+', ' ', clean2).strip()
    print(f"Text preview: {clean2[:400]}")

    page.close()

    # 3. Try /exchanges/ page
    print("\n\n=== /exchanges/ ===")
    page = ctx.new_page()
    url3 = f"https://www.okooo.com/soccer/match/{MID}/exchanges/"
    resp3 = page.goto(url3, wait_until="networkidle", timeout=30000)
    html3 = resp3.body().decode("utf-8", errors="replace")
    print(f"Status: {resp3.status}, Size: {len(html3)}")
    title3 = re.search(r'<title>(.*?)</title>', html3)
    if title3:
        print(f"Title: {title3.group(1)}")
    clean3 = re.sub(r'<script[^>]*>.*?</script>', '', html3, flags=re.DOTALL)
    clean3 = re.sub(r'<style[^>]*>.*?</style>', '', clean3, flags=re.DOTALL)
    clean3 = re.sub(r'<[^>]+>', ' ', clean3)
    clean3 = re.sub(r'\s+', ' ', clean3).strip()
    print(f"Text preview: {clean3[:400]}")
    page.close()

    browser.close()
