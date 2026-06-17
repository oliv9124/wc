"""Validate local odds data completeness vs expectations."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent.parent
W500 = ROOT / "data" / "w500"
QIU_OV = ROOT / "data" / "qiu" / "overview"
KEY_CIDS = ["293", "1055", "3", "2", "280", "9", "6", "5"]


def validate_w500(data):
    """Return list of issue strings for one w500 match file."""
    issues = []
    cos = data.get("companies", {})
    if not cos:
        issues.append("no companies")
        return issues
    eu2 = ah2 = ou2 = 0
    empty_ah_key = []
    for cid in KEY_CIDS:
        c = cos.get(cid)
        if not c:
            continue
        eu_n = len(c.get("eu") or [])
        ah_n = len(c.get("ah") or [])
        ou_n = len(c.get("ou") or [])
        if eu_n >= 2:
            eu2 += 1
        if ah_n >= 2:
            ah2 += 1
        if ou_n >= 2:
            ou2 += 1
        if eu_n >= 2 and ah_n == 0:
            empty_ah_key.append(c.get("name", cid))
    if eu2 >= 3 and ah2 == 0:
        issues.append(f"EU ok({eu2}) but no AH history")
    elif empty_ah_key:
        issues.append(f"AH missing for key cos: {', '.join(empty_ah_key[:4])}")
    if eu2 >= 3 and ou2 == 0:
        issues.append(f"EU ok({eu2}) but no OU history")
    return issues


def validate_qiu(fid):
    issues = []
    for kind in ["ouzhi", "yazhi", "daxiao"]:
        p = QIU_OV / f"{fid}_{kind}.json"
        if not p.exists():
            issues.append(f"missing {kind}")
            continue
        d = json.load(open(p, encoding="utf-8"))
        rows = d.get("rows", [])
        if not rows:
            issues.append(f"empty {kind}")
    return issues


def audit_matches(matches=None, verbose=True):
    config = json.load(open(ROOT / "worldcup_fids.json", encoding="utf-8"))
    matches = matches or config["matches"]
    report = {"ok": 0, "warn": 0, "items": []}
    for m in matches:
        label = f"{m['date']} {m['home']} vs {m['away']}"
        item = {"match": label, "issues": []}
        mid, fid = m.get("w500_mid"), m.get("qiu_fid")
        wp = W500 / f"{mid}.json"
        if not wp.exists():
            item["issues"].append("missing w500 file")
        else:
            item["issues"].extend(validate_w500(json.load(open(wp, encoding="utf-8"))))
        if fid:
            item["issues"].extend(validate_qiu(fid))
        if item["issues"]:
            report["warn"] += 1
            if verbose:
                print(f"⚠ {label}")
                for i in item["issues"]:
                    print(f"    - {i}")
        else:
            report["ok"] += 1
            if verbose:
                print(f"✓ {label}")
        report["items"].append(item)
    return report


def main():
    import argparse
    p = argparse.ArgumentParser(description="Validate WC odds data completeness")
    p.add_argument("--date", help="Only matches on this date (YYYY-MM-DD)")
    p.add_argument("--finished", action="store_true", help="Only finished matches")
    p.add_argument("--json", action="store_true", help="Output JSON summary")
    args = p.parse_args()
    config = json.load(open(ROOT / "worldcup_fids.json", encoding="utf-8"))
    matches = config["matches"]
    if args.date:
        matches = [m for m in matches if m["date"] == args.date]
    if args.finished:
        matches = [m for m in matches if m.get("status") == "finished"]
    if not args.json:
        print(f"Validating {len(matches)} matches...\n")
    report = audit_matches(matches, verbose=not args.json)
    summary = {"total": len(matches), "ok": report["ok"], "warn": report["warn"], "items": report["items"]}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}\nOK: {report['ok']}  WARN: {report['warn']} / {len(matches)}")


if __name__ == "__main__":
    main()
