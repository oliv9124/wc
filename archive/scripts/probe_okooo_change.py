"""Probe okooo change history page structure."""
import sys, json, re, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent

cookie_str = ""
cookie_file = ROOT / "okooo_cookie.txt"
if cookie_file.exists():
    cookie_str = cookie_file.read_text().strip()

# Test match: 墨西哥 vs 南非, mid=1315851
MID = "1315851"
# Test company: Bet365, cid from okooo = look up from data
# From okooo data, Bet365 cid should be around 476 or similar
# Let's first check the list page to find cids
with open(ROOT / "data" / "okooo" / "lists" / f"{MID}_odds_p0.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print("Companies in okooo data:")
for c in d["companies"][:10]:
    print(f"  cid={c['cid']:4} {c['name']}")

# Now try various URL patterns for change history
from playwright.sync_api import sync_playwright

cookies = []
for pair in cookie_str.split("; "):
    if "=" in pair:
        n, v = pair.split("=", 1)
        cookies.append({"name": n, "value": v, "domain": ".okooo.com", "path": "/"})

# Pick a company to test: Bet365
test_cid = None
for c in d["companies"]:
    if "Bet365" in c["name"] or "bet365" in c["name"].lower():
        test_cid = c["cid"]
        print(f"\nUsing Bet365 cid={test_cid}")
        break

if not test_cid:
    test_cid = d["companies"][1]["cid"]
    print(f"\nFallback company cid={test_cid} ({d['companies'][1]['name']})")

# Try different URL patterns
urls_to_try = [
    f"https://www.okooo.com/soccer/match/{MID}/odds/change/{test_cid}/",
    f"https://www.okooo.com/soccer/match/{MID}/odds/{test_cid}/change/",
    f"https://www.okooo.com/soccer/match/{MID}/change/{test_cid}/odds/",
    f"https://www.okooo.com/soccer/match/{MID}/hodds/{test_cid}/",
    f"https://www.okooo.com/soccer/match/{MID}/hodds/",
    f"https://www.okooo.com/soccer/match/{MID}/hah/{test_cid}/",
    f"https://www.okooo.com/soccer/match/{MID}/hah/",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    ctx.add_cookies(cookies)

    for url in urls_to_try:
        print(f"\n--- Trying: {url} ---")
        page = ctx.new_page()
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            status = resp.status
            body = resp.body()
            html = body.decode("utf-8", errors="replace")
            print(f"  Status: {status}, Size: {len(html)}")

            if status == 200 and len(html) > 500:
                # Check for odds-like content
                if "赔率" in html or "变赔" in html or "odds" in html.lower() or re.search(r'\d\.\d{2}', html):
                    print(f"  >>> LOOKS PROMISING!")
                    # Save for analysis
                    outf = ROOT / f"probe_okooo_{url.split('/')[-2]}.html"
                    with open(outf, "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"  Saved to {outf.name}")

                    # Quick content peek
                    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
                    clean = re.sub(r'<[^>]+>', ' ', clean)
                    clean = re.sub(r'\s+', ' ', clean).strip()
                    print(f"  Text preview: {clean[:300]}")
                elif "404" in html or "not found" in html.lower():
                    print(f"  404 content")
                else:
                    print(f"  No odds content found")
                    # Check title
                    title = re.search(r'<title>(.*?)</title>', html)
                    if title:
                        print(f"  Title: {title.group(1)}")
            elif status == 403:
                print(f"  WAF blocked")
            else:
                print(f"  Empty or error")
        except Exception as e:
            print(f"  ERROR: {e}")
        finally:
            page.close()
        time.sleep(2)

    # Also try the main match page to find change history links
    print(f"\n--- Checking main match page for change links ---")
    page = ctx.new_page()
    try:
        url = f"https://www.okooo.com/soccer/match/{MID}/odds/"
        resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
        html = resp.body().decode("utf-8", errors="replace")
        print(f"  Status: {resp.status}, Size: {len(html)}")

        # Find links that might be change history
        links = re.findall(r'href="([^"]*(?:change|history|hodds|hah|detail)[^"]*)"', html, re.IGNORECASE)
        if links:
            print(f"  Found change-related links:")
            for l in set(links):
                print(f"    {l}")
        else:
            print("  No change/history links found directly")
            # Look for any links containing the match id
            match_links = re.findall(r'href="(/soccer/match/' + MID + r'/[^"]*)"', html)
            if match_links:
                print(f"  Match-related links:")
                for l in set(match_links):
                    print(f"    {l}")

        # Check for JS that loads change data
        ajax_urls = re.findall(r'(?:url|href|src)["\s:=]+["\']?([^"\'>\s]*(?:change|history|hodds)[^"\'>\s]*)', html, re.IGNORECASE)
        if ajax_urls:
            print(f"  AJAX/JS change URLs:")
            for u in set(ajax_urls):
                print(f"    {u}")

        outf = ROOT / "probe_okooo_main_odds.html"
        with open(outf, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Saved main page to {outf.name}")

    except Exception as e:
        print(f"  ERROR: {e}")
    finally:
        page.close()

    browser.close()
