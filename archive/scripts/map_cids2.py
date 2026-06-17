"""Extended CID scan + okooo regex extraction."""
from playwright.sync_api import sync_playwright
import json, re, time, urllib.request

KNOWN_CIDS = {0: "百家欧赔", 1: "竞彩官方", 2: "立博", 3: "Bet365", 5: "澳门", 6: "伟德", 9: "易胜博", 16: "10BET", 1055: "Pinnacle"}

OKOOO_COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"

# Overview companies with init odds (from page)
OVERVIEW = [
    ("百家欧赔", "1.46", "4.19", "7.10"),
    ("竞彩官方", "1.34", "3.92", "7.85"),
    ("威廉希尔", "1.57", "3.70", "5.50"),
    ("澳门", "1.45", "3.90", "5.90"),
    ("Bet365", "1.50", "4.00", "5.50"),
    ("立博", "1.48", "4.20", "6.50"),
    ("伟德", "1.45", "4.10", "7.50"),
    ("Pinnacle平博", "1.45", "4.35", "7.19"),
    ("皇冠", "1.51", "4.05", "5.80"),
    ("易胜博", "1.52", "4.10", "5.80"),
    ("金宝博", "1.51", "4.05", "5.80"),
    ("利记", "1.47", "3.73", "5.70"),
    ("香港马会", "1.38", "3.85", "7.35"),
    ("10BET", "1.48", "4.10", "7.20"),
    ("Mansion88(明升)", "1.42", "3.95", "6.40"),
]

def fetch_qiu_init(fid, cid):
    url = f"https://bifen.qiuqiushidao.com/index.php?c=odds&a=oneodds&fid={fid}&cid={cid}&type=ouzhi"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://bifen.qiuqiushidao.com/"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            if data.get("code") == 100 and data.get("data"):
                rec = data["data"][-1]
                return (rec["win"], rec["draw"], rec["lost"]), len(data["data"])
    except:
        pass
    return None, 0

def main():
    fid = "1279645"

    # ============================================================
    # Part 1: Extended qiuqiushidao scan (51-300)
    # ============================================================
    print("=" * 60)
    print("qiuqiushidao: scanning CIDs 51-300")
    print("=" * 60)

    # Already found: 0,1,2,3,4,5,6,8,9,11,14,16,18,1055
    already_found = {
        0: ("1.46", "4.19", "7.10"), 1: ("1.34", "3.92", "7.85"),
        2: ("1.48", "4.20", "6.50"), 3: ("1.50", "4.00", "5.50"),
        4: ("1.50", "4.30", "6.75"), 5: ("1.45", "3.90", "5.90"),
        6: ("1.45", "4.10", "7.50"), 8: ("1.48", "4.00", "6.50"),
        9: ("1.52", "4.10", "5.80"), 11: ("1.44", "3.90", "6.00"),
        14: ("1.53", "4.20", "6.00"), 16: ("1.48", "4.10", "7.20"),
        18: ("1.51", "4.60", "7.80"), 1055: ("1.45", "4.35", "7.19"),
    }

    all_cids = dict(already_found)
    new_found = 0
    for cid in range(51, 301):
        init, count = fetch_qiu_init(fid, cid)
        if init:
            all_cids[cid] = init
            new_found += 1
            print(f"  CID {cid:>5}: init=({init[0]}, {init[1]}, {init[2]}) records={count}")
        time.sleep(0.2)

    print(f"\n  New CIDs found: {new_found}")
    print(f"  Total CIDs: {len(all_cids)}")

    # Match all CIDs to overview names
    print()
    print("=" * 60)
    print("Full CID → Company matching")
    print("=" * 60)
    ov_lookup = {(w, d, l): name for name, w, d, l in OVERVIEW}
    final = {}
    for cid in sorted(all_cids.keys()):
        init = all_cids[cid]
        if cid in KNOWN_CIDS:
            final[cid] = KNOWN_CIDS[cid]
        elif init in ov_lookup:
            final[cid] = ov_lookup[init]
        else:
            final[cid] = f"? init={init}"
        print(f"  CID {cid:>5} = {final[cid]}")

    # ============================================================
    # Part 2: okooo — extract via page HTML content + regex
    # ============================================================
    print()
    print("=" * 60)
    print("okooo: CID extraction via Playwright + regex")
    print("=" * 60)
    cookies = []
    for pair in OKOOO_COOKIE.split("; "):
        if "=" in pair:
            n, v = pair.split("=", 1)
            cookies.append({"name": n, "value": v, "domain": ".okooo.com", "path": "/"})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto(
            "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype=BaijiaBooks",
            wait_until="domcontentloaded", timeout=15000
        )
        html = page.content()
        print(f"  Page HTML length: {len(html)}")

        # Use JS to extract — proper escaping
        okooo_map = page.evaluate("""
            () => {
                const mapping = {};
                const rows = document.querySelectorAll('tr[id]');
                for (const tr of rows) {
                    const m = tr.id.match(/^tr(\\d+)$/);
                    if (!m) continue;
                    const cid = m[1];
                    const nameEl = tr.querySelector('td.namefont span[title]');
                    const countryEl = tr.querySelector('div.countryname');
                    if (nameEl) {
                        mapping[cid] = {
                            name: nameEl.innerText.trim(),
                            country: countryEl ? countryEl.innerText.trim() : ''
                        };
                    }
                }
                return mapping;
            }
        """)
        print(f"  JS extracted: {len(okooo_map)} companies")

        # Fallback: regex on HTML
        if not okooo_map:
            print("  JS failed, trying regex...")
            pattern = r'<tr\s+id="tr(\d+)"[^>]*data-pname="([^"]*)"'
            for m in re.finditer(pattern, html):
                cid = m.group(1)
                raw_name = m.group(2)
                clean_name = re.sub(r"<[^>]+>", "", raw_name)
                okooo_map[cid] = {"name": clean_name, "country": ""}
            print(f"  Regex extracted: {len(okooo_map)} companies")

        for cid in sorted(okooo_map.keys(), key=lambda x: int(x)):
            info = okooo_map[cid]
            print(f"  CID {cid:>5} = {info['name']} ({info['country']})")

        page.close()
        browser.close()

    # Save
    result = {
        "qiuqiushidao": {str(k): v for k, v in final.items()},
        "okooo": okooo_map
    }
    with open(r"D:\Desktop\world cup\cid_mapping.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to cid_mapping.json")

if __name__ == "__main__":
    main()
