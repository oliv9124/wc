import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

COOKIE = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; HMACCOUNT=472E20100B861A48; IMUserID=30727497; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436"
cookies = [{"name": n, "value": v, "domain": ".okooo.com", "path": "/"} for pair in COOKIE.split("; ") if "=" in pair for n, v in [pair.split("=", 1)]]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36", locale="zh-CN")
    ctx.add_cookies(cookies)
    page = ctx.new_page()
    resp = page.goto("https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype=BaijiaBooks", wait_until="domcontentloaded", timeout=15000)
    raw = resp.body()

    # Find data-pname
    idx = raw.find(b"data-pname")
    if idx >= 0:
        chunk = raw[idx:idx+100]
        print("Hex:", chunk.hex())
        print("UTF-8:", chunk.decode("utf-8", errors="replace"))
        print("GBK:", chunk.decode("gbk", errors="replace"))
        print("GB2312:", chunk.decode("gb2312", errors="replace"))

    # Find second data-pname (竞彩官方)
    idx2 = raw.find(b"data-pname", idx + 1)
    if idx2 >= 0:
        chunk2 = raw[idx2:idx2+100]
        print("\n2nd data-pname:")
        print("Hex:", chunk2.hex())
        print("UTF-8:", chunk2.decode("utf-8", errors="replace"))
        print("GBK:", chunk2.decode("gbk", errors="replace"))

    page.close()
    browser.close()
