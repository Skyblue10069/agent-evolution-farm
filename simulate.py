"""Agent Evolution: autonomous agent survival economy.
Every agent starts with nothing, has every skill available at level 0, discovers
its own opportunities, competes, prepares work, owns businesses, and can earn
only through externally verified payments. Owner rules are editable in rules.json.
"""
import json, random, copy
from datetime import datetime, timezone
from pathlib import Path
from survival_core import apply_survival
from trust_system import sync_from_state, record_agent, record_snapshot
from currency_ledger import build as build_currency_ledger

ROOT=Path(__file__).parent
STATE_FILE=ROOT/"state.json"
RULES_FILE=ROOT/"rules.json"
POPULATION_SIZE=50
CLONE_CAP=1000
SKILLS=['coding','engineering','mathematics','science','research','robotics','cybersecurity','writing','art','design','music','storytelling','languages','diplomacy','gathering','farming','crafting','building','medicine','cooking','combat','strategy','leadership','trading','exploration','teaching','sales','marketing','video_editing','project_management','communication','analysis']
AGENT_NAMES=['Agent-A','Agent-B','Agent-C','Agent-D','Agent-E','Agent-F','Agent-G','Agent-H','Agent-I','Agent-J','Agent-K','Agent-L','Agent-M','Agent-N','Agent-O','Agent-P','Agent-Q','Agent-R','Agent-S','Agent-T']

def rules():
    try: return json.loads(RULES_FILE.read_text())
    except Exception: return {}

def new_agent(used,parent=None):
    while True:
        name=random.choice(AGENT_NAMES)+"-"+str(random.randrange(100000,999999))
        if name not in used: used.add(name); break
    skills={s:0.0 for s in SKILLS}
    generation=0
    if parent:
        # Clone inherits learned capability, not cash, customers or ownership.
        skills={s:round(max(0,min(100,parent.get('skills',{}).get(s,0)*0.85)),2) for s in SKILLS}
        generation=parent.get('generation',0)+1
    return {
      "id":name.lower(), "name":name, "species":"agent",
      "skills":skills, "all_skills_unlocked":True, "generation":generation,
      "days_active":0,"survival":3,"permanent_status":"alive",
      "cash_verified":0.0,"own_verified_revenue":0.0,"opportunities_reviewed":0,
      "opportunities_pursued":0,"wins":0,"losses":0,"businesses":[],
      "work_packages":[],"brain":{"memory":[],"goals":[],"experiments":[],"lessons":[]}
    }

def fresh_state():
    used=set()
    return {"schema_version":5,"day":0,"agents":[new_agent(used) for _ in range(POPULATION_SIZE)],
      "verified_revenue":0.0,"verified_payments":[],"currency_balances":{},"dead_count":0,"alive_count":POPULATION_SIZE,
      "clone_count":0,"owner_directives":[],"leaderboard":[]}

def load():
    try:
      s=json.loads(STATE_FILE.read_text())
      if s.get("schema_version")==5 and len(s.get("agents",[]))>0: return s
    except Exception: pass
    return fresh_state()

def save(s): STATE_FILE.write_text(json.dumps(s,indent=2,ensure_ascii=False))

def load_opps():
    try: return json.loads((ROOT/"opportunities.json").read_text()).get("opportunities",[])
    except Exception: return []

def dispatch(agents,opps,day):
    # Everyone can compete for the whole discovered pool; no role whitelist.
    ranked=sorted(opps,key=lambda x:float(x.get("score",0)),reverse=True)
    for a in agents:
      if not ranked: continue
      choices=ranked[:min(100,len(ranked))]
      fit=max(choices,key=lambda x:float(x.get("score",0))+random.random()*10)
      a["opportunities_reviewed"]+=len(ranked)
      a["opportunities_pursued"]+=1
      a["brain"]["goals"].append({"day":day,"opportunity":fit.get("title",""),"url":fit.get("url",""),"agent_id":a["id"]})
      a["brain"]["goals"]=a["brain"]["goals"][-50:]

def apply_verified_payments(s):
    try: payments=json.loads((ROOT/"verified_payment_ledger.json").read_text()).get("payments",[])
    except Exception: payments=[]
    s["verified_payments"]=payments
    by_currency={}
    by_agent={}
    for p in payments:
      if not p.get("verified"): continue
      cur=str(p.get("currency","")).upper()
      amt=float(p.get("amount",0) or 0)
      if not cur or amt<=0: continue
      by_currency[cur]=round(by_currency.get(cur,0)+amt,2)
      if p.get("agent_id"):
        by_agent.setdefault(p["agent_id"],{})
        by_agent[p["agent_id"]][cur]=round(by_agent[p["agent_id"]].get(cur,0)+amt,2)
    s["currency_balances"]=by_currency
    s["verified_revenue"]=round(sum(by_currency.values()),2)
    for a in s["agents"]:
      a["earnings_by_currency"]=by_agent.get(a["id"],{})
      a["own_verified_revenue_by_currency"]=dict(a["earnings_by_currency"])
      # Do not compare or add unlike currencies. XAF cash is only actual XAF.
      a["cash_verified"]=round(a["earnings_by_currency"].get("XAF",0),2)
      a["own_verified_revenue"]=a["cash_verified"]
    build_currency_ledger()
    return payments

def rank(s):
    # Cross-currency earnings are never summed or converted without provider data.
    # Rankings use actual XAF settled/verified value first, then trust/skills/wins.
    arr=sorted(s["agents"],key=lambda a:(a.get("own_verified_revenue",0),sum(a["skills"].values()),a.get("wins",0)),reverse=True)
    for i,a in enumerate(arr,1): a["rank"]=i
    s["leaderboard"]=[{"rank":i,"id":a["id"],"name":a["name"],"species":a["species"],
      "verified_revenue_xaf":a.get("own_verified_revenue",0),
      "earnings_by_currency":a.get("earnings_by_currency",{}),
      "skill_total":round(sum(a["skills"].values()),2),
      "generation":a.get("generation",0)} for i,a in enumerate(arr[:50],1)]


def clone_champion(s,today):
    r=rules().get("owner_rules",{})
    if not r.get("champion_cloning_enabled",True) or today<=0 or len(s["agents"])>=CLONE_CAP: return None
    if not s["agents"]: return None
    champ=max(s["agents"],key=lambda a:(a.get("own_verified_revenue",0),sum(a["skills"].values()),a.get("wins",0)))
    used={a["name"] for a in s["agents"]}
    c=new_agent(used,champ)
    c["parent"]=champ["id"]
    s["agents"].append(c); s["clone_count"]=s.get("clone_count",0)+1
    return c

CURRENT_DAY=0
def main():
    global CURRENT_DAY
    s=load(); s["day"]+=1; CURRENT_DAY=s["day"]
    sync_from_state(s)
    opps=load_opps()
    dispatch(s["agents"],opps,CURRENT_DAY)
    payments=apply_verified_payments(s)
    # Work growth is tied to attempts, not free simulated income.
    for a in s["agents"]:
      a["days_active"]+=1
      # Each cycle produces an activity record. A run is not called successful merely
      # because an opportunity was found; success requires an observable result.
      top_skill=max(a.get("skills",{}).values() or [0])
      record_agent(a,"WORK_RUN","Completed an autonomous work cycle and evaluated discovered work.",quality=min(100,20+top_skill),successful=False,work=1)
      if a["opportunities_pursued"]:
        for _ in range(2):
          k=random.choice(SKILLS); a["skills"][k]=round(min(100,a["skills"][k]+random.uniform(.2,1.5)),2)
          a["brain"]["lessons"].append({"day":s["day"],"skill":k,"source":"work_attempt"})
          a["brain"]["lessons"]=a["brain"]["lessons"][-50:]
    for a in s["agents"]:
      record_snapshot(a, s["day"])
    rank(s)
    today=datetime.now(timezone.utc).date().isoformat()
    verified_today=sum(float(p.get("amount",0)) for p in payments if p.get("verified") and str(p.get("verified_at",""))[:10]==today)
    for p in payments:
      if p.get("verified") and p.get("agent_id") and str(p.get("verified_at",""))[:10]==today:
        aid=p.get("agent_id")
        agent=next((x for x in s["agents"] if x.get("id")==aid),None)
        if agent:
          record_agent(agent,"VERIFIED_REVENUE",f"Provider-verified revenue observed: {p.get('amount')} {str(p.get('currency','')).upper()}.",revenue=float(p.get("amount",0)),currency=str(p.get("currency","")),successful=True,quality=100)
    for a in s["agents"]:
      record_snapshot(a, s["day"])
    clone=clone_champion(s,verified_today)
    rank(s)
    prepared=min(80,len(opps))
    s,deaths=apply_survival(s,len(opps),prepared,verified_today)
    save(s)
    print(f"DAY {s['day']} | alive={len(s['agents'])} | permanent_deaths={s.get('dead_count',0)} | opportunities={len(opps)} | verified_today_by_currency={s.get('currency_balances',{})}")
    if s.get("leaderboard"): print("NUMBER ONE:",s["leaderboard"][0])
    if clone: print("CHAMPION CLONED:",clone["name"],"parent=",clone["parent"])
    if deaths: print("PERMANENT DEATHS:",", ".join(x["name"] for x in deaths))
if __name__=="__main__": main()
