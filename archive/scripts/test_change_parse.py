"""Quick test: fetch and parse okooo change history for 3 companies."""
import json, sys, re, time
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


def parse_change(html):
    records = []
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
    for t in tables:
        trs = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL)
        if len(trs) < 5:
            continue
        first_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', trs[0], re.DOTALL)
        header_text = " ".join(re.sub(r'<[^>]+>', '', c).strip() for c in first_cells)
        if "时间" not in header_text:
            continue
        for tr in trs[2:]:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', td).strip().replace("&nbsp;", "").replace("&uarr;", "").replace("&darr;", "") for td in tds]
            if len(cells) < 11:
                continue
            ts = cells[0].replace("(终)", "").replace("(初)", "").strip()
            if not re.match(r'\d{4}/\d{2}/\d{2}', ts):
                continue
            ts = ts.replace("/", "-")
            is_init = "(初)" in re.sub(r'<[^>]+>', '', tds[0])
            is_final = "(终)" in re.sub(r'<[^>]+>', '', tds[0])
            try:
                rec = {
                    "time": ts,
                    "win": cells[2], "draw": cells[3], "lost": cells[4],
                    "prob_w": cells[5], "prob_d": cells[6], "prob_l": cells[7],
                    "kelly_w": cells[8], "kelly_d": cells[9], "kelly_l": cells[10],
                    "pay": cells[11] if len(cells) > 11 else "",
                }
                if is_init: rec["tag"] = "init"
                elif is_final: rec["tag"] = "final"
                records.append(rec)
            except:
                continue
    return records


MID = "1315851"
test_cids = [27, 82, 250]  # Bet365, 立博, 皇冠

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    ctx.add_cookies(cookies)

    for cid in test_cids:
        url = f"https://www.okooo.com/soccer/match/{MID}/odds/change/{cid}/"
        page = ctx.new_page()
        resp = page.goto(url, wait_until="domcontentloaded", timeout=20000)
        html = resp.body().decode("utf-8", errors="replace")
        records = parse_change(html)
        print(f"cid={cid}: {len(records)} records")
        if records:
            print(f"  First(newest): {json.dumps(records[0], ensure_ascii=False)}")
            print(f"  Last(oldest):  {json.dumps(records[-1], ensure_ascii=False)}")
        page.close()
        time.sleep(3)

    browser.close()
    print("\nDone. Parser works correctly." if all else "Parser might have issues.")
