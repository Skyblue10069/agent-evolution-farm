#!/usr/bin/env python3
"""Agent Evolution improvement layer.

Adds bounded intelligence, adaptive specialization, experiments, competition,
knowledge sharing, recovery, security telemetry, API adapter discovery,
scaling metadata, and a lightweight local dashboard. It never fabricates
customers, work completion, revenue, or payment verification.
"""
from __future__ import annotations
import hashlib, json, math, os, random, shutil, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state.json"
RULES_FILE = ROOT / "rules.json"
UPGRADE_FILE = ROOT / "evolution_upgrade_state.json"
CHECKPOINT_DIR = ROOT / "checkpoints"
DASHBOARD = ROOT / "dashboard.html"
ADAPTERS = ROOT / "api_adapters.json"
SECURITY_LOG = ROOT / "security_audit.jsonl"
LEARNING = ROOT / "long_term_learning.jsonl"

SKILL_GROUPS = {
    "technical": ["coding","engineering","mathematics","science","research","robotics","cybersecurity","analysis"],
    "creative": ["writing","art","design","music","storytelling","video_editing"],
    "commerce": ["sales","marketing","trading","project_management","communication","diplomacy"],
    "operations": ["gathering","farming","crafting","building","cooking","exploration"],
    "leadership": ["strategy","leadership","teaching","languages"],
}

def now(): return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def save_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)

def log(path, event):
    with path.open("a", encoding="utf-8") as f: f.write(json.dumps(event, sort_keys=True) + "\n")

def checkpoint(s, label):
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = CHECKPOINT_DIR / f"state-{stamp}-{label}.json"
    target.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    # Keep bounded history.
    files = sorted(CHECKPOINT_DIR.glob("state-*.json"), key=lambda p:p.stat().st_mtime, reverse=True)
    for old in files[8:]:
        try: old.unlink()
        except OSError: pass
    return str(target)

def skill_total(a): return sum(float(v or 0) for v in a.get("skills", {}).values())

def improve_agent(a, opps, day, rng):
    skills = a.setdefault("skills", {})
    totals = {g: sum(float(skills.get(k,0) or 0) for k in ks) for g,ks in SKILL_GROUPS.items()}
    # Earned specialization: the strongest area gets a small strategic preference,
    # but every skill remains available and trainable.
    focus = max(totals, key=totals.get) if totals else "technical"
    recent = a.setdefault("brain", {}).setdefault("lessons", [])[-20:]
    success = sum(1 for x in recent if x.get("result") == "success")
    attempts = max(1, len(recent))
    confidence = min(0.98, max(0.05, 0.25 + success/attempts*0.55 + skill_total(a)/max(1,len(skills))/100*0.20))
    a["intelligence_profile"] = {
        "confidence": round(confidence,4),
        "specialization": focus,
        "skill_groups": {k: round(v,2) for k,v in totals.items()},
        "uncertainty": round(1-confidence,4),
        "last_updated_day": day,
    }
    a.setdefault("brain", {}).setdefault("plans", []).append({
        "day": day, "focus": focus, "confidence": round(confidence,4),
        "fallback": "review_another_public_opportunity" if confidence < .6 else "continue_current_strategy"
    })
    a["brain"]["plans"] = a["brain"]["plans"][-50:]
    return focus, confidence

def discover_signals(s, opps, day):
    signals=[]
    for o in opps[:2000]:
        title=str(o.get("title", "")); score=float(o.get("score",0) or 0)
        text=(title+" "+str(o.get("description",""))).lower()
        category="general"
        for key, words in {
            "software":["software","developer","api","automation","app"],
            "creative":["design","video","writing","editing","thumbnail"],
            "education":["teach","course","tutor","education"],
            "research":["research","analysis","data","survey"],
            "business":["business","marketing","sales","service"],
        }.items():
            if any(w in text for w in words): category=key; break
        signals.append({"day":day,"category":category,"score":round(score,3),"title":title[:180],"url":o.get("url","")})
    s["opportunity_signals"] = sorted(signals,key=lambda x:x["score"],reverse=True)[:500]

def experiments(s, day):
    exp = s.setdefault("experiments", [])
    for a in s.get("agents",[]):
        if a.get("permanent_status") != "alive": continue
        profile=a.get("intelligence_profile",{})
        focus=profile.get("specialization","general")
        exp.append({"id":f"exp-{day}-{a['id']}","agent_id":a["id"],"day":day,
                    "variant":random.choice(["A","B"]),"strategy":focus,
                    "status":"hypothesis","measured_only_from_verified_results":True})
    s["experiments"] = exp[-5000:]

def share_knowledge(s, day):
    agents=[a for a in s.get("agents",[]) if a.get("permanent_status")=="alive"]
    top=sorted(agents,key=lambda a:(a.get("wins",0),skill_total(a)),reverse=True)[:20]
    library=s.setdefault("shared_knowledge",[])
    for a in top[:5]:
        lessons=a.get("brain",{}).get("lessons",[])[-3:]
        for lesson in lessons:
            library.append({"day":day,"source_agent":a["id"],"lesson":lesson})
    s["shared_knowledge"]=library[-1000:]

def competition(s, day):
    alive=[a for a in s.get("agents",[]) if a.get("permanent_status")=="alive"]
    groups=[]
    # Deterministic batches make 7,777 agents manageable.
    size=64
    for i in range(0,len(alive),size):
        batch=alive[i:i+size]
        batch=sorted(batch,key=lambda a:(a.get("own_verified_revenue",0),a.get("wins",0),skill_total(a)),reverse=True)
        if batch:
            winner=batch[0]; winner["wins"]=int(winner.get("wins",0))+1
            for loser in batch[1:]:
                loser["losses"]=int(loser.get("losses",0))+1
            groups.append({"day":day,"winner":winner["id"],"size":len(batch)})
    s.setdefault("tournaments",[]).extend(groups)
    s["tournaments"]=s["tournaments"][-500:]

def business_metrics(s, day):
    for a in s.get("agents",[]):
        for b in a.get("businesses",[]) or []:
            b.setdefault("metrics",{})
            b["metrics"].update({
                "updated_day":day,
                "verified_revenue_only":True,
                "capacity":b["metrics"].get("capacity",1),
                "status":b.get("status","experimental"),
                "adaptation_score":round(min(100, float(b["metrics"].get("adaptation_score",0))+0.1),2)
            })

def economy_metrics(s):
    balances=s.get("currency_balances",{}) or {}
    xaf=float(balances.get("XAF",0) or 0)
    total=sum(float(v or 0) for v in balances.values())
    s["economy_risk"]={"currencies":len(balances),"xaf_verified":round(xaf,2),
                        "unconverted_total":round(total,2),"cross_currency_sum_is_not_a_ranking":True}

def security_audit(s):
    suspicious_tokens=["api_key=", "password=", "secret=", "private_key=", "seed_phrase="]
    findings=[]
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name in {"security_audit.jsonl"}: continue
        if any(part in {".git","__pycache__"} for part in path.parts): continue
        if path.suffix.lower() not in {".py",".json",".yml",".yaml"}: continue
        try: text=path.read_text(encoding="utf-8",errors="ignore")
        except Exception: continue
        low=text.lower()
        for term in suspicious_tokens:
            if term in low and "getenv" not in low and "secrets." not in low:
                findings.append({"file":str(path.relative_to(ROOT)),"signal":term})
    event={"at":now(),"findings":findings[:100],"status":"review" if findings else "clean"}
    log(SECURITY_LOG,event)
    s["security_status"]=event

def scaling_metadata(s):
    n=len(s.get("agents",[])); workers=max(1, math.ceil(n/500))
    s["scaling"]={"population":n,"recommended_shards":workers,"batch_size":500,
                  "self_modification_batch":int(os.getenv("SELF_MOD_BATCH","100")),
                  "distributed_ready":True,"shared_state":"git-persisted"}

def adapters_manifest(s):
    manifest=load_json(ADAPTERS,{"version":1,"adapters":[]})
    manifest["last_checked"]=now()
    save_json(ADAPTERS,manifest)
    s["api_adapter_status"]={"manifest":str(ADAPTERS.name),"external_credentials_required":True,
                             "providers":[x.get("name") for x in manifest.get("adapters",[])]}

def dashboard(s):
    alive=sum(1 for a in s.get("agents",[]) if a.get("permanent_status")=="alive")
    dead=sum(1 for a in s.get("agents",[]) if a.get("permanent_status")!="alive")
    top=sorted(s.get("agents",[]),key=lambda a:(a.get("own_verified_revenue",0),a.get("wins",0),skill_total(a)),reverse=True)[:20]
    rows="".join(f"<tr><td>{i}</td><td>{a.get('name')}</td><td>{a.get('permanent_status')}</td><td>{a.get('own_verified_revenue',0)}</td><td>{a.get('wins',0)}</td><td>{round(skill_total(a),2)}</td></tr>" for i,a in enumerate(top,1))
    html=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agent Evolution Dashboard</title><style>body{{font-family:system-ui;background:#0b1020;color:#eaf0ff;margin:24px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}.card{{background:#141b30;padding:16px;border-radius:14px}}table{{width:100%;margin-top:20px;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #29314a;text-align:left}}</style></head><body><h1>Agent Evolution</h1><p>Local read-only dashboard generated from persisted state.</p><div class="grid"><div class="card"><b>Population</b><h2>{len(s.get('agents',[]))}</h2></div><div class="card"><b>Alive</b><h2>{alive}</h2></div><div class="card"><b>Permanent deaths</b><h2>{dead}</h2></div><div class="card"><b>Day</b><h2>{s.get('day',0)}</h2></div><div class="card"><b>Verified revenue</b><h2>{s.get('verified_revenue',0)}</h2></div></div><h2>Leaderboard</h2><table><tr><th>#</th><th>Agent</th><th>Status</th><th>Verified XAF</th><th>Wins</th><th>Skill total</th></tr>{rows}</table><p>Generated {now()}</p></body></html>'''
    DASHBOARD.write_text(html,encoding="utf-8")

def main():
    s=load_json(STATE_FILE,{})
    if not s.get("agents"): print("No state.json agents found"); return 1
    day=int(s.get("day",0)); opps=load_json(ROOT/"opportunities.json",{}).get("opportunities",[])
    checkpoint(s,"pre-upgrade")
    discover_signals(s,opps,day)
    for a in s.get("agents",[]):
        if a.get("permanent_status")=="alive": improve_agent(a,opps,day,random)
    experiments(s,day); share_knowledge(s,day); competition(s,day); business_metrics(s,day); economy_metrics(s)
    security_audit(s); scaling_metadata(s); adapters_manifest(s)
    s["upgrade_meta"]={"last_run":now(),"features":["adaptive_intelligence","experiments","knowledge_sharing","competition","business_adaptation","economy_risk","security_audit","scaling","api_adapter_manifest","recovery_checkpoints","dashboard","long_term_learning"]}
    log(LEARNING,{"day":day,"at":now(),"population":len(s.get("agents",[])),"verified_revenue":s.get("verified_revenue",0),"lesson":"improvement cycle completed from observed state"})
    save_json(STATE_FILE,s); dashboard(s); checkpoint(s,"post-upgrade")
    print(f"EVOLUTION UPGRADE: day={day} agents={len(s['agents'])} alive={sum(a.get('permanent_status')=='alive' for a in s['agents'])}")
    return 0

if __name__=="__main__": raise SystemExit(main())
