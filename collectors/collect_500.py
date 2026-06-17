"""500.com World Cup odds change history collector."""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
CONFIG = ROOT / "worldcup_fids.json"
OUT_DIR = ROOT / "data" / "w500"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Referer": "https://odds.500.com/",
}

KEY_CIDS = ["293", "1055", "3", "2", "280", "9", "6", "348", "651", "5", "11", "4", "8", "14"]

CID_NAMES = {
    "293": "威廉希尔", "1055": "Pinnacle", "3": "Bet365", "2": "立博",
    "280": "皇冠", "9": "易胜博", "6": "伟德", "348": "金宝博",
    "651": "利记", "5": "澳门", "11": "Bwin", "4": "Interwetten",
    "8": "SNAI", "14": "Coral", "16": "10BET", "1487": "沙巴",
    "1488": "188bet", "18": "Mansion", "0": "竞彩官方",
}

DELAY = 0.35
MAX_RETRIES = 3


# ── Step 1: Discover 500.com match IDs ──

def discover_candidates(dates):
    seen = set()
    candidates = []
    for d in dates:
        url = f"https://live.500.com/?e={d}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            for mid in re.findall(r"ouzhi-(\d+)", r.text):
                if mid not in seen:
                    seen.add(mid)
                    candidates.append(mid)
        except Exception as e:
            print(f"  [WARN] live page {d} failed: {e}")
        time.sleep(DELAY)
    return candidates


def identify_wc_match(mid):
    url = f"https://odds.500.com/fenxi/ouzhi-{mid}.shtml"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = "gbk"
        m = re.search(r"<title>(.+?)</title>", r.text)
        if not m:
            return None
        title = m.group(1)
        if "世界杯" not in title:
            return None
        tm = re.match(r"(.+?)VS(.+?)\(", title)
        if not tm:
            return None
        return (tm.group(1).strip(), tm.group(2).strip())
    except Exception:
        return None


def build_mid_map(config):
    matches = config["matches"]
    dates_needed = sorted(set(m["date"] for m in matches))
    live_dates = []
    for d in dates_needed:
        parts = d.split("-")
        y, mo, dy = int(parts[0]), int(parts[1]), int(parts[2])
        live_dates.append(d)
        prev_day = f"{y}-{mo:02d}-{dy-1:02d}"
        if prev_day not in live_dates:
            live_dates.append(prev_day)
    live_dates = sorted(set(live_dates))

    print(f"[1/4] Scanning live pages: {live_dates}")
    candidates = discover_candidates(live_dates)
    print(f"  Found {len(candidates)} candidate match IDs")

    print("[2/4] Identifying World Cup matches...")
    wc_matches = {}
    for i, mid in enumerate(candidates):
        teams = identify_wc_match(mid)
        if teams:
            wc_matches[mid] = teams
            print(f"  ✓ {mid}: {teams[0]} vs {teams[1]}")
        if (i + 1) % 10 == 0:
            print(f"  ... checked {i+1}/{len(candidates)}")
        time.sleep(DELAY)
    print(f"  Found {len(wc_matches)} World Cup matches")

    mid_map = {}
    for match in matches:
        home, away = match["home"], match["away"]
        key = f"{home}_{away}"
        for mid, (h, a) in wc_matches.items():
            if (home in h or h in home) and (away in a or a in away):
                mid_map[key] = mid
                break
        if key not in mid_map:
            for mid, (h, a) in wc_matches.items():
                if home[:2] in h and away[:2] in a:
                    mid_map[key] = mid
                    break

    print(f"  Mapped {len(mid_map)}/{len(matches)} matches")
    for match in matches:
        key = f"{match['home']}_{match['away']}"
        mid = mid_map.get(key, "?")
        status = "✓" if mid != "?" else "✗"
        print(f"  {status} {match['home']} vs {match['away']} → {mid}")
    return mid_map


# ── Step 2: Get company list ──

def get_companies(mid):
    url = f"https://odds.500.com/fenxi/ouzhi-{mid}.shtml"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.encoding = "gbk"
    html = r.text
    companies = {}
    for m in re.finditer(r'<tr[^>]*\bid=["\'](\d+)["\']', html):
        cid = m.group(1)
        start = m.end()
        chunk = html[start : start + 500]
        nm = re.search(r'class=["\']tb_plgs["\'][^>]*>(.*?)</td>', chunk, re.DOTALL)
        name = re.sub(r"<[^>]*>", "", nm.group(1)).strip() if nm else cid
        companies[cid] = name
    return companies


# ── Step 3: Fetch change history ──

def fetch_eu(mid, cid):
    url = f"https://odds.500.com/fenxi1/json/ouzhi.php?fid={mid}&cid={cid}&r=1&type=europe"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.json() if r.text.strip() else []
    except Exception:
        return []


def parse_html_rows(raw_text):
    try:
        arr = json.loads(raw_text)
    except Exception:
        return []
    results = []
    for row_html in arr:
        unescaped = re.sub(
            r"\\u([0-9a-fA-F]{4})",
            lambda m: chr(int(m.group(1), 16)),
            row_html,
        )
        cells = []
        for cell in unescaped.split("</td>"):
            clean = re.sub(r"<[^>]*>", "", cell).replace("&nbsp;", " ").strip()
            if clean:
                cells.append(clean)
        if len(cells) >= 3:
            results.append(cells)
    return results


def fetch_ah(mid, cid):
    url = f"https://odds.500.com/fenxi1/inc/yazhiajax.php?fid={mid}&id={cid}&r=1"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return parse_html_rows(r.text)
    except Exception:
        return []


def fetch_ou(mid, cid):
    t = int(time.time() * 1000)
    url = f"https://odds.500.com/fenxi1/inc/daxiaoajax.php?fid={mid}&id={cid}&t={t}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return parse_html_rows(r.text)
    except Exception:
        return []


def fetch_with_retry(fetch_fn, mid, cid, label):
    for attempt in range(MAX_RETRIES):
        data = fetch_fn(mid, cid)
        if data:
            return data
        if attempt < MAX_RETRIES - 1:
            time.sleep(1.5 * (attempt + 1))
    print(f"      [WARN] {label} empty after {MAX_RETRIES} retries")
    return []


def validate_match_data(data):
    """Return issues list; empty means structurally ok."""
    issues = []
    cos = data.get("companies", {})
    eu_ok = ah_ok = ou_ok = 0
    for cid in KEY_CIDS[:8]:
        c = cos.get(cid)
        if not c:
            continue
        if len(c.get("eu") or []) >= 2:
            eu_ok += 1
        if len(c.get("ah") or []) >= 2:
            ah_ok += 1
        if len(c.get("ou") or []) >= 2:
            ou_ok += 1
    if eu_ok >= 3 and ah_ok == 0:
        issues.append("ah_empty")
    if eu_ok >= 3 and ou_ok == 0:
        issues.append("ou_empty")
    return issues


# ── Step 4: Collect everything ──

def collect_company(mid, cid, name):
    eu = fetch_with_retry(fetch_eu, mid, cid, f"{name} EU")
    time.sleep(DELAY)
    ah = fetch_with_retry(fetch_ah, mid, cid, f"{name} AH")
    time.sleep(DELAY)
    ou = fetch_with_retry(fetch_ou, mid, cid, f"{name} OU")
    time.sleep(DELAY)
    return {
        "name": CID_NAMES.get(cid, name),
        "eu": eu,
        "ah": ah,
        "ou": ou,
    }


def collect_match(mid, match_info, target_cids=None):
    all_companies = get_companies(mid)
    time.sleep(DELAY)
    cids = [c for c in (target_cids or all_companies.keys()) if c in all_companies]

    print(f"  Collecting {len(cids)} companies (of {len(all_companies)} available)...")
    result = {
        "mid": mid,
        "home": match_info["home"],
        "away": match_info["away"],
        "date": match_info["date"],
        "time": match_info["time"],
        "group": match_info.get("group", ""),
        "total_companies": len(all_companies),
        "collected_ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "companies": {},
    }
    for i, cid in enumerate(cids):
        name = all_companies[cid]
        result["companies"][cid] = collect_company(mid, cid, name)
        c = result["companies"][cid]
        print(f"    [{i+1}/{len(cids)}] {name}(cid={cid}): EU={len(c['eu'])} AH={len(c['ah'])} OU={len(c['ou'])}")
    return result


def repair_match_file(path, mid):
    """Re-fetch empty AH/OU for companies that have EU history."""
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    for cid, c in data.get("companies", {}).items():
        eu_n = len(c.get("eu") or [])
        if eu_n < 2:
            continue
        name = c.get("name", cid)
        if len(c.get("ah") or []) == 0:
            c["ah"] = fetch_with_retry(fetch_ah, mid, cid, f"{name} AH repair")
            if c["ah"]:
                fixed += 1
            time.sleep(DELAY)
        if len(c.get("ou") or []) == 0:
            c["ou"] = fetch_with_retry(fetch_ou, mid, cid, f"{name} OU repair")
            if c["ou"]:
                fixed += 1
            time.sleep(DELAY)
    data["collected_ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["repaired_ts"] = data["collected_ts"]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return fixed, validate_match_data(data)


def filter_matches(matches, date=None, finished=False):
    if date:
        matches = [m for m in matches if m["date"] == date]
    if finished:
        matches = [m for m in matches if m.get("status") == "finished"]
    return matches


def main():
    parser = argparse.ArgumentParser(description="500.com World Cup odds collector")
    parser.add_argument("--force", action="store_true", help="Re-collect even if file exists")
    parser.add_argument("--repair", action="store_true", help="Re-fetch empty AH/OU in existing files")
    parser.add_argument("--date", help="Only matches on YYYY-MM-DD")
    parser.add_argument("--finished", action="store_true", help="Only finished matches")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    matches = filter_matches(config["matches"], args.date, args.finished)

    mid_map_file = OUT_DIR / "mid_map.json"
    if mid_map_file.exists():
        mid_map = json.loads(mid_map_file.read_text(encoding="utf-8"))
        print(f"Loaded existing mid_map: {len(mid_map)} entries")
    else:
        mid_map = build_mid_map(config)
        mid_map_file.write_text(json.dumps(mid_map, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved mid_map to {mid_map_file}")

    print(f"\nTargets: {len(matches)} matches")

    if args.repair:
        print("\n[repair] Re-fetching empty AH/OU...")
        repaired, warned = 0, 0
        for match in matches:
            key = f"{match['home']}_{match['away']}"
            mid = mid_map.get(key)
            if not mid:
                continue
            path = OUT_DIR / f"{mid}.json"
            if not path.exists():
                continue
            n, issues = repair_match_file(path, mid)
            label = f"{match['home']} vs {match['away']}"
            if n:
                repaired += 1
                print(f"  ✓ {label}: fixed {n} company fields")
            if issues:
                warned += 1
                print(f"  ⚠ {label}: still has {issues}")
        print(f"\nRepair done. {repaired} files updated, {warned} still incomplete.")
        return

    print("\n[collect] Odds change history...")
    collected = 0
    for match in matches:
        key = f"{match['home']}_{match['away']}"
        mid = mid_map.get(key)
        if not mid:
            print(f"  ✗ {match['home']} vs {match['away']} — no 500.com ID, skipping")
            continue

        out_file = OUT_DIR / f"{mid}.json"
        if out_file.exists() and not args.force:
            print(f"  → {match['home']} vs {match['away']} ({mid}) — exists, skip (use --force)")
            collected += 1
            continue

        print(f"  → {match['home']} vs {match['away']} ({mid})")
        data = collect_match(mid, match, target_cids=KEY_CIDS)
        issues = validate_match_data(data)
        if issues:
            print(f"  ⚠ Validation: {issues}")
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        collected += 1
        print(f"  Saved {out_file.name} ({len(data['companies'])} companies)")

    print(f"\nDone. {collected}/{len(matches)} files present → {OUT_DIR}")


if __name__ == "__main__":
    main()
