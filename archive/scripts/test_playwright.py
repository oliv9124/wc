from playwright.sync_api import sync_playwright
import json, time

COOKIE_STR = "LastUrl=; PHPSESSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; pm=; _ga=GA1.1.1713008827.1781265552; Hm_lvt_213d524a1d07274f17dfa17b79db318f=1781265554; HMACCOUNT=472E20100B861A48; FirstURL=www.okooo.com/livecenter/; FirstOKURL=https%3A//www.okooo.com/soccer/match/1315851/history/; First_Source=www.okooo.com; IMUserID=30727497; IMUserName=%E7%89%B9%E4%B9%94276358; OKSID=73e6b03dd58bef821b81b6ebc2401c909f203a7b; M_UserName=%22%5Cu7279%5Cu4e54276358%22; M_UserID=30727497; M_Ukey=01d582b08762342671a45bf5629711f0; OkAutoUuid=afecd549fa62ec291d9f57ed69496309; OkMsIndex=4; acw_tc=76b20fb317812674418085738e435a5031524736b867b675380fa61ce6f436; Hm_lpvt_213d524a1d07274f17dfa17b79db318f=1781268448"

URLS = [
    ("oe/change", "https://www.okooo.com/soccer/match/1315851/oe/change/2/"),
    ("htft/change", "https://www.okooo.com/soccer/match/1315851/htft/change/2/"),
    ("odds/ajax", "https://www.okooo.com/soccer/match/1315851/odds/ajax/?page=0&trnum=0&companytype=BaijiaBooks"),
]

def parse_cookies(cookie_str):
    cookies = []
    for pair in cookie_str.split("; "):
        if "=" in pair:
            name, value = pair.split("=", 1)
            cookies.append({"name": name, "value": value, "domain": ".okooo.com", "path": "/"})
    return cookies

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            locale="zh-CN",
            viewport={"width": 1920, "height": 1080},
        )
        context.add_cookies(parse_cookies(COOKIE_STR))

        for name, url in URLS:
            page = context.new_page()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = resp.status if resp else "no response"
                content = page.content()
                is_waf = "405" in str(status) or "阻断" in content or "blocked" in content.lower()
                print(f"[{name}] status={status}, length={len(content)}, waf={'YES' if is_waf else 'NO'}")
            except Exception as e:
                print(f"[{name}] ERROR: {e}")
            finally:
                page.close()
            time.sleep(2)

        browser.close()

if __name__ == "__main__":
    main()
