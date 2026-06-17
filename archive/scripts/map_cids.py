"""Map company CIDs for both qiuqiushidao and okooo."""
from playwright.sync_api import sync_playwright
import json, re, time, urllib.request

KNOWN_CIDS = {0: "百家欧赔", 1: "竞彩官方", 2: "立博", 3: "Bet365", 5: "澳门", 6: "伟德", 9: "易胜博", 16: "10BET", 1055: "Pinnacle"}

OKOOO_COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"

# ============================================================
# Part 1: qiuqiushidao — scan CIDs, match by initial odds
# ============================================================

def fetch_qiu_odds(fid, cid):
    url = f"https://bifen.qiuqiushidao.com/index.php?c=odds&a=oneodds&fid={fid}&cid={cid}&type=ouzhi"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://bifen.qiuqiushidao.com/"
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            if data.get("code") == 100 and data.get("data"):
                records = data["data"]
                initial = records[-1]  # oldest record = initial odds
                latest = records[0]    # newest record = current odds
                return {
                    "init": (initial["win"], initial["draw"], initial["lost"]),
                    "curr": (latest["win"], latest["draw"], latest["lost"]),
                    "count": len(records)
                }
    except:
        pass
    return None

def scan_qiu_cids(fid):
    print("Scanning qiuqiushidao CIDs...")
    results = {}
    # Scan 0-50 and some higher ranges
    scan_ranges = list(range(0, 51)) + list(range(1050, 1060))
    for cid in scan_ranges:
        odds = fetch_qiu_odds(fid, cid)
        if odds:
            name = KNOWN_CIDS.get(cid, "???")
            results[cid] = {"name": name, **odds}
            print(f"  CID {cid:>5} = {name:<15} init=({odds['init'][0]}, {odds['init'][1]}, {odds['init'][2]})  records={odds['count']}")
        time.sleep(0.3)
    return results

# ============================================================
# Part 2: Parse overview page to get company names + init odds
# ============================================================

def parse_qiu_overview(fid):
    url = f"https://bifen.qiuqiushidao.com/index.php?c=home&a=ouzhi&fid={fid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://bifen.qiuqiushidao.com/"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    companies = []
    pattern = r'<p>赔率公司：(.+?)</p>\s*<p>即时赔率：1、初始赔率：胜：([\d.]+)，平：([\d.]+)，负：([\d.]+)'
    for m in re.finditer(pattern, html):
        companies.append({
            "name": m.group(1),
            "init": (m.group(2), m.group(3), m.group(4))
        })
    return companies

# ============================================================
# Part 3: okooo — extract CID map via Playwright
# ============================================================

def extract_okooo_cids():
    print("\nExtracting okooo CID mapping via Playwright...")
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

        js_code = """
        () => {
            const rows = document.querySelectorAll('tr[id^="tr"]');
            const mapping = {};
            rows.forEach(tr => {
                const idMatch = tr.id.match(/^tr(\\d+)$/);
                if (!idMatch) return;
                const cid = idMatch[1];
                const nameEl = tr.querySelector('.JsCountryName > span[title]');
                const countryEl = tr.querySelector('.countryname');
                if (nameEl) {
                    const rawName = nameEl.textContent.trim();
                    const country = countryEl ? countryEl.textContent.trim() : '';
                    mapping[cid] = { name: rawName, country: country };
                }
            });
            return mapping;
        }
        """
        okooo_map = page.evaluate(js_code)
        page.close()
        browser.close()
    return okooo_map

# ============================================================
# Main
# ============================================================

def main():
    fid = "1279645"  # Mexico vs South Africa

    # Step 1: Parse overview page for company names + initial odds
    print("=" * 60)
    print("Step 1: qiuqiushidao overview companies")
    print("=" * 60)
    overview = parse_qiu_overview(fid)
    for i, c in enumerate(overview):
        print(f"  {i+1:>2}. {c['name']:<20} init=({c['init'][0]}, {c['init'][1]}, {c['init'][2]})")

    # Step 2: Scan CIDs and match by initial odds
    print()
    print("=" * 60)
    print("Step 2: qiuqiushidao CID scan")
    print("=" * 60)
    scanned = scan_qiu_cids(fid)

    # Step 3: Match scanned CIDs to overview company names
    print()
    print("=" * 60)
    print("Step 3: Matching CIDs to company names")
    print("=" * 60)
    final_qiu = {}
    for cid, info in scanned.items():
        if info["name"] != "???":
            final_qiu[cid] = info["name"]
            continue
        for ov in overview:
            if info["init"] == ov["init"]:
                final_qiu[cid] = ov["name"]
                print(f"  MATCHED: CID {cid} = {ov['name']} (by init odds {ov['init']})")
                break
        else:
            final_qiu[cid] = f"Unknown (init={info['init']})"
            print(f"  UNMATCHED: CID {cid}, init={info['init']}")

    print(f"\n  Total qiuqiushidao companies: {len(final_qiu)}")
    for cid in sorted(final_qiu.keys()):
        print(f"  CID {cid:>5} = {final_qiu[cid]}")

    # Step 4: okooo CID mapping
    print()
    print("=" * 60)
    print("Step 4: okooo CID mapping")
    print("=" * 60)
    okooo_map = extract_okooo_cids()
    print(f"  Found {len(okooo_map)} companies:")
    for cid in sorted(okooo_map.keys(), key=lambda x: int(x)):
        info = okooo_map[cid]
        print(f"  CID {cid:>5} = {info['name']} ({info['country']})")

    # Save all results
    result = {
        "qiuqiushidao": {str(k): v for k, v in final_qiu.items()},
        "okooo": okooo_map
    }
    with open(r"D:\Desktop\world cup\cid_mapping.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nAll mappings saved to cid_mapping.json")

if __name__ == "__main__":
    main()
