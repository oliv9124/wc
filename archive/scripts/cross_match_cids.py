"""Cross-reference qiuqiushidao unknown CIDs with okooo by matching odds."""
import sys, json, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"
cookies = [{"name": n, "value": v, "domain": ".okooo.com", "path": "/"} for pair in COOKIE.split("; ") if "=" in pair for n, v in [pair.split("=", 1)]]

# qiuqiushidao unknown CIDs with their init odds
QIU_UNKNOWN = {
    4: ("1.50", "4.30", "6.75"),
    8: ("1.48", "4.00", "6.50"),
    11: ("1.44", "3.90", "6.00"),
    14: ("1.53", "4.20", "6.00"),
    18: ("1.51", "4.60", "7.80"),
    67: ("1.52", "4.10", "7.10"),
    70: ("1.50", "4.20", "5.75"),
    78: ("1.52", "4.20", "6.25"),
    80: ("1.40", "4.20", "7.50"),
    92: ("1.50", "4.25", "6.25"),
    94: ("1.45", "4.50", "8.00"),
    103: ("1.47", "4.10", "5.50"),
    108: ("1.48", "4.30", "7.10"),
    132: ("1.44", "4.10", "6.75"),
    142: ("1.52", "4.40", "7.40"),
    155: ("1.43", "4.00", "6.70"),
    163: ("1.44", "4.20", "7.00"),
    182: ("1.53", "4.00", "5.75"),
    195: ("1.36", "4.33", "8.50"),
    216: ("1.49", "4.20", "6.60"),
    223: ("1.50", "4.35", "8.00"),
    234: ("1.41", "4.39", "9.23"),
    250: ("1.44", "4.05", "7.50"),
    263: ("1.44", "4.10", "6.25"),
    275: ("1.49", "4.20", "6.75"),
    291: ("1.52", "4.10", "6.00"),
    # Also from the 300-651 scan
    310: ("1.44", "3.99", "7.11"),
    350: ("1.43", "4.40", "8.50"),
    388: ("1.44", "4.30", "8.20"),
    391: ("1.45", "4.50", "7.00"),
    418: ("1.45", "4.20", "8.00"),
    422: ("1.50", "4.20", "6.00"),
    451: ("1.50", "3.80", "6.00"),
    453: ("1.48", "4.30", "7.70"),
    502: ("1.38", "4.55", "8.70"),
    537: ("1.45", "4.15", "7.40"),
    544: ("1.30", "4.01", "6.95"),
    578: ("1.47", "3.90", "5.50"),
    591: ("1.45", "4.00", "6.50"),
    623: ("1.54", "4.10", "6.30"),
    625: ("1.47", "4.10", "6.40"),
    626: ("1.46", "4.00", "6.50"),
    650: ("1.47", "4.20", "7.00"),
}

# Get okooo initial odds for all 122 companies
print("Fetching okooo initial odds for cross-matching...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        locale="zh-CN",
    )
    ctx.add_cookies(cookies)

    okooo_odds = {}  # cid -> {name, init_odds}

    for pg in range(0, 5):
        page = ctx.new_page()
        url = f"https://www.okooo.com/soccer/match/1315851/odds/ajax/?page={pg}&trnum=0&companytype=BaijiaBooks"
        resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
        html = resp.body().decode("utf-8", errors="replace")

        # Extract each company's init odds (csObj columns have init odds)
        for tr_m in re.finditer(r'<tr\s+id="tr(\d+)"[^>]*data-pname="([^"]*)".*?</tr>', html, re.DOTALL):
            cid = tr_m.group(1)
            raw_name = tr_m.group(2)
            clean_name = re.sub(r"<span[^>]*style='font-size:0;'[^>]*>[^<]*</span>", "", raw_name)
            block = tr_m.group(0)

            # Init odds are in csObj spans: <td ... class="... csObj" ...><span ...>1.52</span></td>
            init_odds = re.findall(r'csObj"[^>]*>[^<]*<span[^>]*>([\d.]+)</span>', block)
            if len(init_odds) >= 3:
                okooo_odds[cid] = {
                    "name": clean_name,
                    "init": (init_odds[0], init_odds[1], init_odds[2])
                }

        page.close()
        time.sleep(2)

    browser.close()

print(f"Got init odds for {len(okooo_odds)} okooo companies")

# Build reverse lookup: init_odds -> okooo company name
odds_to_name = {}
for cid, info in okooo_odds.items():
    key = info["init"]
    if key not in odds_to_name:
        odds_to_name[key] = []
    odds_to_name[key].append(f"{info['name']}(ok_cid={cid})")

# Match qiuqiushidao unknowns
print(f"\n{'='*70}")
print("Cross-matching qiuqiushidao unknown CIDs with okooo init odds")
print(f"{'='*70}")

matched = {}
unmatched = {}
for qiu_cid, init in sorted(QIU_UNKNOWN.items()):
    if init in odds_to_name:
        names = odds_to_name[init]
        matched[qiu_cid] = names[0] if len(names) == 1 else " | ".join(names)
        print(f"  qiu CID {qiu_cid:>5} = {matched[qiu_cid]}  (init {init})")
    else:
        unmatched[qiu_cid] = init

print(f"\nMatched: {len(matched)}, Unmatched: {len(unmatched)}")
if unmatched:
    print("\nUnmatched CIDs:")
    for cid, init in sorted(unmatched.items()):
        print(f"  qiu CID {cid:>5}: init={init}")

# Save results
with open(r"D:\Desktop\world cup\qiu_cid_crossmatch.json", "w", encoding="utf-8") as f:
    json.dump({"matched": {str(k): v for k, v in matched.items()}, "unmatched": {str(k): list(v) for k, v in unmatched.items()}}, f, ensure_ascii=False, indent=2)
print(f"\nSaved to qiu_cid_crossmatch.json")
