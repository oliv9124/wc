"""Generate standalone HTML dashboard with all match data."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).parent
DATA = ROOT / "data"
config = json.load(open(ROOT / "worldcup_fids.json", "r", encoding="utf-8"))

def load_j(p):
    if not p.exists(): return None
    return json.load(open(p, "r", encoding="utf-8"))

matches = []
for m in config["matches"]:
    fid, mid = m["qiu_fid"], m.get("ok_mid","")
    entry = {"date": m["date"], "time": m["time"], "group": m["group"],
             "home": m["home"], "away": m["away"], "score": m.get("score",""),
             "status": m.get("status",""), "fid": fid, "mid": mid}

    # Qiu EU
    eu = load_j(DATA / "qiu" / "overview" / f"{fid}_ouzhi.json")
    if eu:
        rows = []
        for r in eu.get("rows", []):
            fd = r.get("first",{})
            ed = r.get("end") or fd
            if not isinstance(fd, dict) or not isinstance(ed, dict): continue
            rows.append([r.get("name",""), r.get("id",""),
                         fd.get("win",""),fd.get("draw",""),fd.get("lost",""),
                         ed.get("win",""),ed.get("draw",""),ed.get("lost",""),
                         ed.get("pay","")])
        entry["qe"] = rows

    # Qiu AH
    ah = load_j(DATA / "qiu" / "overview" / f"{fid}_yazhi.json")
    if ah:
        rows = []
        for r in ah.get("rows", []):
            fd = r.get("first",{})
            ed = r.get("end") or fd
            if not isinstance(fd, dict) or not isinstance(ed, dict): continue
            rows.append([r.get("name",""),
                         fd.get("home",""),fd.get("handi",""),fd.get("away",""),
                         ed.get("home",""),ed.get("handi",""),ed.get("away","")])
        entry["qa"] = rows

    # Qiu OU
    ou = load_j(DATA / "qiu" / "overview" / f"{fid}_daxiao.json")
    if ou:
        rows = []
        for r in ou.get("rows", []):
            fd = r.get("first",{})
            ed = r.get("end") or fd
            if not isinstance(fd, dict) or not isinstance(ed, dict): continue
            rows.append([r.get("name",""),
                         fd.get("big",""),fd.get("handi",""),fd.get("small",""),
                         ed.get("big",""),ed.get("handi",""),ed.get("small","")])
        entry["qo"] = rows

    # Okooo EU (from list pages)
    ok_eu = []
    for pg in range(5):
        d = load_j(DATA / "okooo" / "lists" / f"{mid}_odds_p{pg}.json")
        if not d or not d.get("companies"): continue
        for c in d["companies"]:
            row = [c.get("name",""), c.get("cid","")]
            ini = c.get("init",{})
            cur = c.get("curr",{})
            row += [ini.get("win",""),ini.get("draw",""),ini.get("lost","")] if ini else ["","",""]
            row += [cur.get("win",""),cur.get("draw",""),cur.get("lost","")] if cur else ["","",""]
            row += c.get("kelly",[]) if c.get("kelly") else []
            ok_eu.append(row)
    if ok_eu:
        entry["oe"] = ok_eu

    # Okooo AH (from list pages)
    ok_ah = []
    for pg in range(3):
        d = load_j(DATA / "okooo" / "lists" / f"{mid}_ah_p{pg}.json")
        if not d or not d.get("companies"): continue
        for c in d["companies"]:
            ok_ah.append([c.get("name",""), c.get("cid","")]+ c.get("raw_spans",[])[:8])
    if ok_ah:
        entry["oa"] = ok_ah

    matches.append(entry)

data_json = json.dumps(matches, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>世界杯赔率数据总览</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:16px}}
h1{{font-size:20px;font-weight:500;margin-bottom:16px;color:#58a6ff}}
.date-group{{margin-bottom:24px}}
.date-hdr{{font-size:15px;color:#8b949e;padding:6px 0;border-bottom:1px solid #21262d}}
.match{{background:#161b22;border:1px solid #21262d;border-radius:8px;margin:8px 0;overflow:hidden}}
.match-hdr{{display:flex;align-items:center;padding:10px 16px;cursor:pointer;gap:12px}}
.match-hdr:hover{{background:#1c2128}}
.time{{color:#8b949e;font-size:13px;min-width:42px}}
.teams{{flex:1;font-size:15px}}
.score{{font-size:16px;font-weight:600;color:#f0883e;min-width:40px;text-align:center}}
.group{{font-size:12px;color:#8b949e;background:#21262d;padding:2px 8px;border-radius:4px}}
.status{{font-size:12px;padding:2px 8px;border-radius:4px}}
.status.finished{{background:#1b3a2d;color:#3fb950}}
.status.upcoming{{background:#2a1f0b;color:#d29922}}
.tabs{{display:flex;gap:0;border-bottom:1px solid #21262d}}
.tab{{padding:8px 16px;cursor:pointer;font-size:13px;color:#8b949e;border-bottom:2px solid transparent}}
.tab:hover{{color:#c9d1d9}}
.tab.active{{color:#58a6ff;border-bottom-color:#58a6ff}}
.panel{{display:none;padding:8px 12px;max-height:500px;overflow-y:auto}}
.panel.active{{display:block}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;color:#8b949e;padding:4px 6px;border-bottom:1px solid #21262d;position:sticky;top:0;background:#161b22}}
td{{padding:3px 6px;border-bottom:1px solid #21262d22}}
tr:hover td{{background:#1c212833}}
.chg-up{{color:#3fb950}}
.chg-dn{{color:#f85149}}
.detail{{display:none}}
.detail.open{{display:block}}
.no-data{{color:#484f58;font-style:italic;padding:12px;font-size:13px}}
.arrow{{color:#484f58;transition:transform .2s}}
.arrow.open{{transform:rotate(90deg)}}
</style>
</head>
<body>
<h1>2026世界杯 赔率数据总览</h1>
<div id="app"></div>
<script>
const M={data_json};
const byDate={{}};
M.forEach(m=>{{(byDate[m.date]=byDate[m.date]||[]).push(m)}});

function cmp(a,b){{return a<b?-1:a>b?1:0}}
function chgClass(a,b){{
  let fa=parseFloat(a),fb=parseFloat(b);
  if(isNaN(fa)||isNaN(fb))return'';
  return fb<fa?'chg-dn':fb>fa?'chg-up':'';
}}
function renderEU(rows, isOkooo){{
  if(!rows||!rows.length)return'<div class="no-data">无数据</div>';
  let h='<table><tr><th>公司</th><th colspan="3">初盘 (胜/平/负)</th><th colspan="3">终盘 (胜/平/负)</th>';
  if(!isOkooo)h+='<th>返还</th>';
  else h+='<th colspan="3">凯利</th>';
  h+='</tr>';
  rows.forEach(r=>{{
    if(isOkooo){{
      let i=r.slice(2,5),e=r.slice(5,8),k=r.slice(8,11);
      h+=`<tr><td>${{r[0]}}</td><td>${{i[0]}}</td><td>${{i[1]}}</td><td>${{i[2]}}</td>`;
      h+=`<td class="${{chgClass(i[0],e[0])}}">${{e[0]}}</td><td class="${{chgClass(i[1],e[1])}}">${{e[1]}}</td><td class="${{chgClass(i[2],e[2])}}">${{e[2]}}</td>`;
      h+=`<td>${{k[0]||''}}</td><td>${{k[1]||''}}</td><td>${{k[2]||''}}</td></tr>`;
    }}else{{
      h+=`<tr><td>${{r[0]}}</td><td>${{r[2]}}</td><td>${{r[3]}}</td><td>${{r[4]}}</td>`;
      h+=`<td class="${{chgClass(r[2],r[5])}}">${{r[5]}}</td><td class="${{chgClass(r[3],r[6])}}">${{r[6]}}</td><td class="${{chgClass(r[4],r[7])}}">${{r[7]}}</td>`;
      h+=`<td>${{r[8]}}</td></tr>`;
    }}
  }});
  return h+'</table>';
}}
function renderAH(rows, isOkooo){{
  if(!rows||!rows.length)return'<div class="no-data">无数据</div>';
  if(isOkooo){{
    let h='<table><tr><th>公司</th><th colspan="8">数据</th></tr>';
    rows.forEach(r=>{{h+=`<tr><td>${{r[0]}}</td>`+r.slice(2).map(v=>`<td>${{v}}</td>`).join('')+'</tr>'}});
    return h+'</table>';
  }}
  let h='<table><tr><th>公司</th><th colspan="3">初盘 (主/盘/客)</th><th colspan="3">终盘 (主/盘/客)</th></tr>';
  rows.forEach(r=>{{
    h+=`<tr><td>${{r[0]}}</td><td>${{r[1]}}</td><td>${{r[2]}}</td><td>${{r[3]}}</td>`;
    h+=`<td class="${{chgClass(r[1],r[4])}}">${{r[4]}}</td><td>${{r[5]}}</td><td>${{r[6]}}</td></tr>`;
  }});
  return h+'</table>';
}}
function renderOU(rows){{
  if(!rows||!rows.length)return'<div class="no-data">无数据</div>';
  let h='<table><tr><th>公司</th><th colspan="3">初盘 (大/盘/小)</th><th colspan="3">终盘 (大/盘/小)</th></tr>';
  rows.forEach(r=>{{
    h+=`<tr><td>${{r[0]}}</td><td>${{r[1]}}</td><td>${{r[2]}}</td><td>${{r[3]}}</td>`;
    h+=`<td>${{r[4]}}</td><td>${{r[5]}}</td><td>${{r[6]}}</td></tr>`;
  }});
  return h+'</table>';
}}

let html='';
Object.keys(byDate).sort().forEach(date=>{{
  html+=`<div class="date-group"><div class="date-hdr">${{date}}</div>`;
  byDate[date].forEach((m,i)=>{{
    const id=m.fid;
    const hasOE=m.oe&&m.oe.length>0;
    const hasOA=m.oa&&m.oa.length>0;
    html+=`<div class="match"><div class="match-hdr" onclick="toggle('${{id}}')">
      <span class="arrow" id="arr_${{id}}">&#9654;</span>
      <span class="time">${{m.time}}</span>
      <span class="teams">${{m.home}} vs ${{m.away}}</span>
      <span class="score">${{m.score||'-'}}</span>
      <span class="group">${{m.group}}组</span>
      <span class="status ${{m.status}}">${{m.status==='finished'?'完':'待'}}</span>
    </div>
    <div class="detail" id="det_${{id}}">
      <div class="tabs">
        <div class="tab active" onclick="switchTab('${{id}}','qe',this)">球球·欧赔</div>
        <div class="tab" onclick="switchTab('${{id}}','qa',this)">球球·亚盘</div>
        <div class="tab" onclick="switchTab('${{id}}','qo',this)">球球·大小球</div>
        ${{hasOE?`<div class="tab" onclick="switchTab('${{id}}','oe',this)">澳客·欧赔</div>`:''}}
        ${{hasOA?`<div class="tab" onclick="switchTab('${{id}}','oa',this)">澳客·亚盘</div>`:''}}
      </div>
      <div class="panel active" id="p_${{id}}_qe">${{renderEU(m.qe,false)}}</div>
      <div class="panel" id="p_${{id}}_qa">${{renderAH(m.qa,false)}}</div>
      <div class="panel" id="p_${{id}}_qo">${{renderOU(m.qo)}}</div>
      ${{hasOE?`<div class="panel" id="p_${{id}}_oe">${{renderEU(m.oe,true)}}</div>`:''}}
      ${{hasOA?`<div class="panel" id="p_${{id}}_oa">${{renderAH(m.oa,true)}}</div>`:''}}
    </div></div>`;
  }});
  html+='</div>';
}});
document.getElementById('app').innerHTML=html;

function toggle(id){{
  const d=document.getElementById('det_'+id);
  const a=document.getElementById('arr_'+id);
  d.classList.toggle('open');
  a.classList.toggle('open');
}}
function switchTab(id, tab, el){{
  const det=document.getElementById('det_'+id);
  det.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  det.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('p_'+id+'_'+tab).classList.add('active');
}}
</script>
</body></html>"""

out = ROOT / "dashboard.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Dashboard written to {out} ({len(html)} bytes)")
