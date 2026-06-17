from playwright.sync_api import sync_playwright
import json, re, time

COOKIE_STR = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; pm=; _ga=GA1.1.1713008827.1781265552; Hm_lvt_213d524a1d07274f17dfa17b79db318f=1781265554; HMACCOUNT=472E20100B861A48; FirstURL=www.okooo.com/livecenter/; FirstOKURL=https%3A//www.okooo.com/soccer/match/1315851/history/; First_Source=www.okooo.com; IMUserID=30727497; IMUserName=%E7%89%B9%E4%B9%94276358; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserName=%22%5Cu7279%5Cu4e54276358%22; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; OkMsIndex=4; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436; Hm_lpvt_213d524a1d07274f17dfa17b79db318f=1781268448"

def parse_cookies(cookie_str):
    cookies = []
    for pair in cookie_str.split("; "):
        if "=" in pair:
            name, value = pair.split("=", 1)
            cookies.append({"name": name, "value": value, "domain": ".okooo.com", "path": "/"})
    return cookies

def extract_okooo_cids(page):
    """Extract CID -> company name mapping from okooo odds list page via JS"""
    return page.evaluate("""() => {
        const rows = document.querySelectorAll('tr.fTrObj');
        const mapping = {};
        rows.forEach(tr => {
            const input = tr.querySelector('input.numclass');
            const nameSpan = tr.querySelector('.JsCountryName > span[title]');
            const countryDiv = tr.querySelector('.countryname');
            if (input && nameSpan) {
                const cid = input.value;
                // Get clean text (strips hidden anti-scraping spans)
                const name = nameSpan.textContent.replace(/[!#@$%^&*]/g, '').trim();
                const country = countryDiv ? countryDiv.textContent.trim() : '';
                mapping[cid] = { name: name, country: country };
            }
        });
        return mapping;
    }""")

def extract_qiuqiushidao_cids():
    """Extract CID mapping from qiuqiushidao overview page"""
    import urllib.request
    url = "https://bifen.qiuqiushidao.com/index.php?c=home&a=ouzhi&fid=1279645"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://bifen.qiuqiushidao.com/"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    pattern = r"showOdds\((\d+)\)"
    cids_found = set(re.findall(pattern, html))

    name_pattern = r'<td[^>]*class="[^"]*"[^>]*>\s*<a[^>]*showOdds\((\d+)\)[^>]*>([^<]+)</a>'
    matches = re.findall(name_pattern, html)
    mapping = {}
    for cid, name in matches:
        mapping[cid] = name.strip()

    if not mapping:
        name_pattern2 = r'showOdds\((\d+)\)[^"]*"[^>]*>([^<]{2,30})</a>'
        matches = re.findall(name_pattern2, html)
        for cid, name in matches:
            mapping[cid] = name.strip()

    return mapping, cids_found, html

def main():
    # --- qiuqiushidao ---
    print("=" * 60)
    print("球球是道 CID mapping")
    print("=" * 60)
    try:
        mapping_q, all_cids, html = extract_qiuqiushidao_cids()
        if mapping_q:
            for cid, name in sorted(mapping_q.items(), key=lambda x: int(x[0])):
                print(f"  CID {cid:>5} = {name}")
        else:
            print("  Regex didn't match, saving HTML for inspection...")
            with open(r"D:\Desktop\world cup\qiu_ouzhi_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Saved to qiu_ouzhi_page.html ({len(html)} chars)")
            print(f"  All CIDs found via showOdds(): {sorted(all_cids, key=lambda x: int(x))}")
    except Exception as e:
        print(f"  Error: {e}")

    print()

    # --- okooo ---
    print("=" * 60)
    print("澳客 CID mapping")
    print("=" * 60)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        context.add_cookies(parse_cookies(COOKIE_STR))

        page = context.new_page()
        resp = page.goto(
            "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype=BaijiaBooks",
            wait_until="domcontentloaded", timeout=15000
        )
        print(f"  Status: {resp.status}, fetching CID map...")
        okooo_map = extract_okooo_cids(page)
        print(f"  Found {len(okooo_map)} companies:")
        for cid, info in sorted(okooo_map.items(), key=lambda x: int(x[0])):
            print(f"  CID {cid:>5} = {info['name']} ({info['country']})")

        page.close()
        browser.close()

    # Save results
    result = {"okooo": okooo_map}
    with open(r"D:\Desktop\world cup\cid_mapping.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to cid_mapping.json")

if __name__ == "__main__":
    main()
