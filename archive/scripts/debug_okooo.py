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

    # Save raw HTML for inspection
    html = page.content()
    with open(r"D:\Desktop\world cup\okooo_pw_raw.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Debug DOM structure
    js = """
    () => {
        const allTr = document.querySelectorAll('tr');
        const withId = document.querySelectorAll('tr[id]');
        const sample = [];
        for (let i = 0; i < Math.min(5, allTr.length); i++) {
            sample.push({
                tag: allTr[i].tagName,
                id: allTr[i].id || '(none)',
                cls: allTr[i].className || '(none)',
                attrKeys: Array.from(allTr[i].attributes).map(a => a.name),
            });
        }
        return {
            totalTr: allTr.length,
            withIdTr: withId.length,
            bodyChildCount: document.body ? document.body.childElementCount : -1,
            firstBodyTag: document.body ? document.body.children[0]?.tagName : 'N/A',
            sample: sample,
        };
    }
    """
    info = page.evaluate(js)
    print(json.dumps(info, ensure_ascii=False, indent=2))

    page.close()
    browser.close()
