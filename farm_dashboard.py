"""Generate a static dashboard from persisted state; it performs no external actions."""
import json
from pathlib import Path
ROOT=Path(__file__).parent

def main():
    try: s=json.loads((ROOT/"state.json").read_text())
    except Exception: s={"agents":[]}
    agents=s.get("agents",[])
    alive=sum(a.get("permanent_status")=="alive" for a in agents)
    dead=len(agents)-alive
    top=sorted(agents,key=lambda a:(a.get("own_verified_revenue",0),sum(a.get("skills",{}).values())),reverse=True)[:10]
    html=f'''<!doctype html><meta charset="utf-8"><title>Agent Evolution Dashboard</title><style>body{{font-family:system-ui;background:#101318;color:#eee;padding:24px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card{{background:#1b2028;padding:16px;border-radius:12px}}table{{width:100%;margin-top:20px}}td,th{{padding:8px;text-align:left}}</style><h1>Agent Evolution</h1><div class="grid"><div class="card">Day<br><b>{s.get('day',0)}</b></div><div class="card">Alive<br><b>{alive}</b></div><div class="card">Dead<br><b>{dead}</b></div><div class="card">Verified XAF<br><b>{s.get('verified_revenue',0)}</b></div></div><h2>Top agents</h2><table><tr><th>#</th><th>Agent</th><th>Verified XAF</th><th>Generation</th><th>Skills</th></tr>'''
    for i,a in enumerate(top,1): html+=f"<tr><td>{i}</td><td>{a.get('name')}</td><td>{a.get('own_verified_revenue',0)}</td><td>{a.get('generation',0)}</td><td>{sum(a.get('skills',{}).values()):.2f}</td></tr>"
    html+='</table>'
    (ROOT/"dashboard.html").write_text(html)
if __name__=="__main__": main()
