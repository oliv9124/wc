"""球球是道 overview odds collector — uses POST JSON API."""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
CONFIG = ROOT / "worldcup_fids.json"
OUT_DIR = ROOT / "data" / "qiu" / "overview"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Referer": "https://bifen.qiuqiushidao.com/",
    "X-Requested-With": "XMLHttpRequest",
}

BASE = "https://bifen.qiuqiushidao.com/index.php"
ENDPOINTS = {
    "ouzhi": "c=odds&a=ouzhi",
    "yazhi": "c=odds&a=yazhi",
    "daxiao": "c=odds&a=daxiao",
}

DELAY = 1.0


def fetch_overview(fid, kind):
    url = f"{BASE}?{ENDPOINTS[kind]}"
    try:
        r = requests.post(url, data={"fid": fid}, headers=HEADERS, timeout=30)
        j = r.json()
        if j.get("code", 0) > 0 and j.get("data"):
            return j["data"]
        return None
    except Exception as e:
        print(f"    [ERROR] {kind}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Qiuqiushidao overview collector")
    parser.add_argument("date", nargs="?", help="Only matches on YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--finished", action="store_true", help="Only finished matches")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    matches = config["matches"]
    if args.date:
        matches = [m for m in matches if m["date"] == args.date]
    if args.finished:
        matches = [m for m in matches if m.get("status") == "finished"]

    if not matches:
        print("No matches found.")
        return

    print(f"Collecting qiu overview for {len(matches)} matches...")

    for match in matches:
        fid = match["qiu_fid"]
        label = f"{match['home']} vs {match['away']} ({match['date']} {match['time']})"
        print(f"\n  {label} [fid={fid}]")

        for kind in ["ouzhi", "yazhi", "daxiao"]:
            out_file = OUT_DIR / f"{fid}_{kind}.json"
            if out_file.exists() and not args.force:
                rows = len(json.loads(out_file.read_text(encoding="utf-8")).get("rows", []))
                print(f"    {kind}: skip (exists, {rows} rows)")
                continue
            data = fetch_overview(fid, kind)
            if data:
                out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                rows = len(data.get("rows", data.get("list", [])))
                print(f"    {kind}: {rows} rows -> {out_file.name}")
            else:
                print(f"    {kind}: FAILED")
            time.sleep(DELAY)

    print("\nDone.")


if __name__ == "__main__":
    main()
