"""Extract okooo CID mapping by loading AJAX HTML into a temp DOM."""
from playwright.sync_api import sync_playwright
import json

COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"

cookies = []
for pair in COOKIE.split("; "):
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
        wait_until="domcontentloaded", timeout=15000,
    )

    # Get raw HTML text from the <pre> tag, then parse it via a temp DOM element
    okooo_map = page.evaluate("""
    () => {
        const pre = document.querySelector('pre');
        if (!pre) return { error: 'no pre element' };

        const rawHtml = pre.textContent;

        // Create a temp container to parse the HTML
        const container = document.createElement('div');
        container.innerHTML = rawHtml;

        const mapping = {};
        const rows = container.querySelectorAll('tr[id]');
        for (const tr of rows) {
            const m = tr.id.match(/^tr(\\d+)$/);
            if (!m) continue;
            const cid = m[1];
            // Company name is in span[title] inside td.namefont
            const nameEl = tr.querySelector('td.namefont span[title]');
            const countryEl = tr.querySelector('div.countryname');
            if (nameEl) {
                mapping[cid] = {
                    name: nameEl.innerText.trim(),
                    country: countryEl ? countryEl.innerText.trim() : ''
                };
            }
        }
        return { count: Object.keys(mapping).length, data: mapping };
    }
    """)

    print(f"Extracted: {okooo_map.get('count', 0)} companies")
    if okooo_map.get("error"):
        print(f"Error: {okooo_map['error']}")
    else:
        data = okooo_map.get("data", {})
        for cid in sorted(data.keys(), key=lambda x: int(x)):
            info = data[cid]
            print(f"  CID {cid:>5} = {info['name']} ({info['country']})")

        # Save
        with open(r"D:\Desktop\world cup\okooo_cid_mapping.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to okooo_cid_mapping.json")

    page.close()
    browser.close()
