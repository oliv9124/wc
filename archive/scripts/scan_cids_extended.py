"""Scan qiuqiushidao CIDs 300-600 to find 皇冠 and 利记."""
import sys, json, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TARGET_HUANGGUAN = ("1.51", "4.05", "5.80")  # 皇冠 init odds (same as 金宝博)
TARGET_LIJI = ("1.47", "3.73", "5.70")        # 利记 init odds

def fetch_qiu_init(fid, cid):
    url = f"https://bifen.qiuqiushidao.com/index.php?c=odds&a=oneodds&fid={fid}&cid={cid}&type=ouzhi"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://bifen.qiuqiushidao.com/"
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            if data.get("code") == 100 and data.get("data"):
                rec = data["data"][-1]
                return (rec["win"], rec["draw"], rec["lost"]), len(data["data"])
    except:
        pass
    return None, 0

fid = "1279645"
found_hg = None
found_lj = None

print("Scanning CIDs 300-600...")
for cid in range(300, 601):
    if cid == 280:  # already known
        continue
    init, count = fetch_qiu_init(fid, cid)
    if init:
        label = ""
        if init == TARGET_HUANGGUAN:
            label = " <<<< 皇冠 MATCH!"
            found_hg = cid
        elif init == TARGET_LIJI:
            label = " <<<< 利记 MATCH!"
            found_lj = cid
        print(f"  CID {cid:>5}: init=({init[0]}, {init[1]}, {init[2]}) records={count}{label}")
    time.sleep(0.2)

    if found_hg and found_lj:
        print("\nBoth found! Stopping early.")
        break

if not found_hg or not found_lj:
    print(f"\nAfter 300-600: 皇冠={'found CID '+str(found_hg) if found_hg else 'NOT FOUND'}, 利记={'found CID '+str(found_lj) if found_lj else 'NOT FOUND'}")
    if not found_hg or not found_lj:
        print("Continuing scan 601-1000...")
        for cid in range(601, 1001):
            init, count = fetch_qiu_init(fid, cid)
            if init:
                label = ""
                if init == TARGET_HUANGGUAN and not found_hg:
                    label = " <<<< 皇冠 MATCH!"
                    found_hg = cid
                elif init == TARGET_LIJI and not found_lj:
                    label = " <<<< 利记 MATCH!"
                    found_lj = cid
                print(f"  CID {cid:>5}: init=({init[0]}, {init[1]}, {init[2]}) records={count}{label}")
            time.sleep(0.2)
            if found_hg and found_lj:
                print("\nBoth found!")
                break

print(f"\n=== RESULT ===")
print(f"皇冠: CID {found_hg}" if found_hg else "皇冠: NOT FOUND")
print(f"利记: CID {found_lj}" if found_lj else "利记: NOT FOUND")
