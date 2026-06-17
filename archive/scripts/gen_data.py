"""Generate compact JSON for widget — only essential odds data."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent
DATA = ROOT / "data"
config = json.load(open(ROOT / "worldcup_fids.json", "r", encoding="utf-8"))

def load_j(p):
    if not p.exists(): return None
    return json.load(open(p, "r", encoding="utf-8"))

def compact_odds(fd, ed):
    return {"i": [fd.get("win",""), fd.get("draw",""), fd.get("lost","")],
            "e": [ed.get("win",""), ed.get("draw",""), ed.get("lost","")]}

def compact_ah(fd, ed):
    return {"i": [fd.get("home",""), fd.get("handi",""), fd.get("away","")],
            "e": [ed.get("home",""), ed.get("handi",""), ed.get("away","")]}

results = []
for m in config["matches"]:
    fid, mid = m["qiu_fid"], m.get("ok_mid","")
    entry = {"d": m["date"], "t": m["time"], "g": m["group"],
             "h": m["home"], "a": m["away"], "s": m.get("score",""),
             "st": m.get("status",""), "fid": fid, "mid": mid}

    # Qiu EU odds (compact)
    eu = load_j(DATA / "qiu" / "overview" / f"{fid}_ouzhi.json")
    if eu:
        q_eu = []
        for r in eu.get("rows", []):
            fd, ed = r.get("first",{}), r.get("end") or r.get("first",{})
            if not isinstance(fd, dict) or not isinstance(ed, dict):
                continue
            q_eu.append({"n": r.get("name",""), "id": r.get("id",""),
                         **compact_odds(fd, ed),
                         "p": ed.get("pay","")})
        entry["qe"] = q_eu

    # Qiu AH (compact)
    ah = load_j(DATA / "qiu" / "overview" / f"{fid}_yazhi.json")
    if ah:
        q_ah = []
        for r in ah.get("rows", []):
            fd, ed = r.get("first",{}), r.get("end") or r.get("first",{})
            if not isinstance(fd, dict) or not isinstance(ed, dict):
                continue
            q_ah.append({"n": r.get("name",""), **compact_ah(fd, ed)})
        entry["qa"] = q_ah

    # Qiu OU (compact)
    ou = load_j(DATA / "qiu" / "overview" / f"{fid}_daxiao.json")
    if ou:
        q_ou = []
        for r in ou.get("rows", []):
            fd, ed = r.get("first",{}), r.get("end") or r.get("first",{})
            if not isinstance(fd, dict) or not isinstance(ed, dict):
                continue
            q_ou.append({"n": r.get("name",""),
                         "i": [fd.get("big",""), fd.get("handi",""), fd.get("small","")],
                         "e": [ed.get("big",""), ed.get("handi",""), ed.get("small","")]})
        entry["qo"] = q_ou

    # Okooo EU odds (from list pages)
    ok_eu = []
    for pg in range(5):
        d = load_j(DATA / "okooo" / "lists" / f"{mid}_odds_p{pg}.json")
        if not d or not d.get("companies"): continue
        for c in d["companies"]:
            row = {"n": c.get("name",""), "cid": c.get("cid","")}
            if c.get("init"):
                row["i"] = [c["init"].get("win",""), c["init"].get("draw",""), c["init"].get("lost","")]
            if c.get("curr"):
                row["e"] = [c["curr"].get("win",""), c["curr"].get("draw",""), c["curr"].get("lost","")]
            if c.get("kelly"):
                row["k"] = c["kelly"]
            ok_eu.append(row)
    if ok_eu:
        entry["oe"] = ok_eu

    # Okooo AH (from list pages)
    ok_ah = []
    for pg in range(3):
        d = load_j(DATA / "okooo" / "lists" / f"{mid}_ah_p{pg}.json")
        if not d or not d.get("companies"): continue
        for c in d["companies"]:
            ok_ah.append({"n": c.get("name",""), "cid": c.get("cid",""),
                          "s": c.get("raw_spans", [])})
    if ok_ah:
        entry["oa"] = ok_ah

    results.append(entry)

print(json.dumps(results, ensure_ascii=False))
