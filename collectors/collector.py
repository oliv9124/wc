"""
World Cup Odds Data Collector
=============================
球球是道: urllib (JSON API, no WAF)

Usage:
  python collector.py qiu          # 球球是道 overview + time series
"""

import json, os, re, sys, time, random, urllib.request, argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
CONFIG = ROOT / "worldcup_fids.json"
CID_MAP = ROOT / "cid_mapping_final.json"

# Key companies for time series (qiuqiushidao CIDs)
QIU_KEY_CIDS = [0, 1055, 3, 293, 2, 280, 9, 6, 348, 651]
QIU_TYPES = ["ouzhi", "yazhi", "daxiao"]
QIU_BASE = "https://bifen.qiuqiushidao.com/index.php"


def load_config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cid_map():
    with open(CID_MAP, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sleep_random(lo=1.0, hi=2.5):
    time.sleep(random.uniform(lo, hi))


# ============================================================
# 球球是道
# ============================================================

def qiu_fetch(url, retries=2):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": QIU_BASE,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
    }
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt < retries:
                time.sleep(3)
            else:
                print(f"    FAILED: {e}")
                return None


def collect_qiu_overview(matches):
    """Fetch overview (all companies snapshot) for each match × each type."""
    out_dir = DATA_DIR / "qiu" / "overview"
    total = len(matches) * len(QIU_TYPES)
    done = 0

    for match in matches:
        fid = match["qiu_fid"]
        label = f"{match['home']}vs{match['away']}"
        for t in QIU_TYPES:
            out_file = out_dir / f"{fid}_{t}.json"
            done += 1
            if out_file.exists():
                print(f"  [{done}/{total}] {label} {t} — skip (exists)")
                continue

            url = f"{QIU_BASE}?c=odds&a={t}&fid={fid}"
            data = qiu_fetch(url)
            if data and data.get("code") == 100:
                rows = data.get("data", {}).get("rows", [])
                save_json(out_file, data["data"])
                print(f"  [{done}/{total}] {label} {t} — {len(rows)} companies")
            else:
                print(f"  [{done}/{total}] {label} {t} — FAILED")
            sleep_random(1.0, 2.0)


def collect_qiu_timeseries(matches):
    """Fetch full odds history for key companies × each match × each type."""
    out_dir = DATA_DIR / "qiu" / "timeseries"
    total = len(matches) * len(QIU_KEY_CIDS) * len(QIU_TYPES)
    done = 0

    for match in matches:
        fid = match["qiu_fid"]
        label = f"{match['home']}vs{match['away']}"
        for cid in QIU_KEY_CIDS:
            for t in QIU_TYPES:
                out_file = out_dir / f"{fid}_{cid}_{t}.json"
                done += 1
                if out_file.exists():
                    print(f"  [{done}/{total}] {label} cid={cid} {t} — skip")
                    continue

                url = f"{QIU_BASE}?c=odds&a=oneodds&fid={fid}&cid={cid}&type={t}"
                data = qiu_fetch(url)
                if data and data.get("code") == 100:
                    records = data.get("data", [])
                    save_json(out_file, {"fid": fid, "cid": cid, "type": t, "records": records})
                    print(f"  [{done}/{total}] {label} cid={cid} {t} — {len(records)} records")
                else:
                    save_json(out_file, {"fid": fid, "cid": cid, "type": t, "records": [], "error": True})
                    print(f"  [{done}/{total}] {label} cid={cid} {t} — no data")
                sleep_random(1.0, 2.0)


def run_qiu(matches):
    print("=" * 60)
    print(f"球球是道: {len(matches)} matches")
    print("=" * 60)

    print("\n--- Phase 1: Overview (all companies snapshot) ---")
    collect_qiu_overview(matches)

    print("\n--- Phase 2: Time series (key companies) ---")
    print(f"  Companies: {len(QIU_KEY_CIDS)}, Types: {len(QIU_TYPES)}")
    collect_qiu_timeseries(matches)

    print("\n球球是道 collection complete.")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="World Cup Odds Collector")
    parser.add_argument("target", choices=["qiu"], help="Data source")
    parser.add_argument("--matches", type=str, help="Comma-separated fid list (default: all)")
    parser.add_argument("--days", type=int, help="Only matches within N days from today")
    args = parser.parse_args()

    config = load_config()
    matches = config["matches"]

    if args.matches:
        fids = set(args.matches.split(","))
        matches = [m for m in matches if m["qiu_fid"] in fids]

    if args.days is not None:
        today = datetime.now().strftime("%Y-%m-%d")
        cutoff = (datetime.now() + timedelta(days=args.days)).strftime("%Y-%m-%d")
        matches = [m for m in matches if today <= m["date"] <= cutoff]

    print(f"Matches to collect: {len(matches)}")
    print(f"Data directory: {DATA_DIR}")
    print()

    run_qiu(matches)

    print("\nDone.")


if __name__ == "__main__":
    main()
