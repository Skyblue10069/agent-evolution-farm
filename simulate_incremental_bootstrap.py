"""Agent Evolution: autonomous agent survival economy.
Every agent starts with nothing, has every skill available at level 0, discovers
its own opportunities, competes, prepares work, owns businesses, and can earn
only through externally verified payments. Owner rules are editable in rules.json.
"""
import json, random, copy, os, argparse, time
from datetime import datetime, timezone
from pathlib import Path
from survival_core import apply_survival
from trust_system import sync_from_state, record_agent, record_snapshot
from currency_ledger import build as build_currency_ledger

ROOT=Path(__file__).parent
STATE_FILE=ROOT/"state.json"
RULES_FILE=ROOT/"rules.json"
POPULATION_SIZE=int(os.getenv("AGENT_POPULATION_SIZE", "7777"))
CLONE_CAP=max(POPULATION_SIZE, int(os.getenv("AGENT_CLONE_CAP", "12000")))
SUBAGENT_CAP=max(POPULATION_SIZE, int(os.getenv("SUBAGENT_CAP", "20000")))
SKILLS=['coding','engineering','mathematics','science','research','robotics','cybersecurity','writing','art','design','music','storytelling','languages','diplomacy','gathering','farming','crafting','building','medicine','cooking','combat','strategy','leadership','trading','exploration','teaching','sales','marketing','video_editing','project_management','communication','analysis']
AGENT_NAMES=['Agent-A','Agent-B','Agent-C','Agent-D','Agent-E','Agent-F','Agent-G','Agent-H','Agent-I','Agent-J','Agent-K','Agent-L','Agent-M','Agent-N','Agent-O','Agent-P','Agent-Q','Agent-R','Agent-S','Agent-T']

def rules():
    try: return json.loads(RULES_FILE.read_text())
    except Exception: return {}

def new_agent(used,parent=None, special=None):
    while True:
        name=random.choice(AGENT_NAMES)+"-"+str(random.randrange(100000,999999))
        if name not in used: used.add(name); break
    skills={s:0.0 for s in SKILLS}
    generation=0
    if parent:
        # Clone inherits learned capability, not cash, customers or ownership.
        skills={s:round(max(0,min(100,parent.get('skills',{}).get(s,0)*0.85)),2) for s in SKILLS}
        generation=parent.get('generation',0)+1
    if special:
        name = special.get("name", name)
        while name in used and name != special.get("name"):
            name = special.get("name", name) + "-CORE"
        used.add(name)
        species = special.get("species", "ai")
    else:
        species = "agent"
    return {
      "id":name.lower().replace(" ","-"), "name":name, "species":species,
      "skills":skills, "all_skills_unlocked":True, "generation":generation,
      "days_active":0,"survival":3,"permanent_status":"alive",
      "cash_verified":0.0,"own_verified_revenue":0.0,"opportunities_reviewed":0,
      "opportunities_pursued":0,"wins":0,"losses":0,"businesses":[],
      "work_packages":[],"active_work":[],"completed_work":0,"failed_work":0,
      "brain":{"memory":[],"goals":[],"experiments":[],"lessons":[],"self_model":{},"plans":[],"critic_notes":[]},
      "traits":{},"genome":{"traits":{},"mutations":0,"lineage":[]},
      "hierarchy":{"parent_id": parent.get("id") if parent else None, "children":[], "spawned_subagents":0, "wants_subagents":False, "depth": int(parent.get("hierarchy",{}).get("depth",0))+1 if parent else 0},
      "main_character":False,"protected_identity":False,"memory_budget_mb":1
    }

def _new_base_state():
    return {"schema_version":6,"day":0,"agents":[],"verified_revenue":0.0,"verified_payments":[],"completed_work_total":0,"unfinished_work_total":0,"currency_balances":{},"dead_count":0,"alive_count":0,"clone_count":0,"owner_directives":[],"leaderboard":[],"bootstrap_complete":False}

def _ensure_cactus(s, used):
    if any(a.get("name") == "Cactus Needle" for a in s.get("agents",[])): return
    c=new_agent(used, special={"name":"Cactus Needle","species":"ai"})
    c["main_character"]=True; c["protected_identity"]=True; c["memory_budget_mb"]=14
    c["brain"]["self_model"]={"identity":"Cactus Needle","role":"main_character_ai","memory_core":"14MB","mission":"learn, complete work, improve, compete, and survive"}
    s.setdefault("agents",[]).append(c)

def fresh_state(): return _new_base_state()

def _bootstrap_population(s):
    target=max(1, POPULATION_SIZE); batch=max(1,int(os.getenv("AGENT_BOOTSTRAP_BATCH","1000"))); budget=max(5.0,float(os.getenv("AGENT_BOOTSTRAP_SECONDS","240")))
    used={a.get("name") for a in s.get("agents",[]) if a.get("name")}; _ensure_cactus(s,used)
    started=time.monotonic(); created=0
    while len(s["agents"])<target and created<batch and time.monotonic()-started<budget:
        s["agents"].append(new_agent(used)); created+=1
    s["alive_count"]=sum(1 for a in s["agents"] if a.get("permanent_status")=="alive"); s["bootstrap_complete"]=len(s["agents"])>=target
    s["bootstrap_target"]=target; s["bootstrap_created_last_run"]=created; s["bootstrap_updated_at"]=datetime.now(timezone.utc).isoformat()
    return created,s["bootstrap_complete"]

def bootstrap_only():
    s=load(); created,complete=_bootstrap_population(s); save(s)
    print(f"POPULATION BOOTSTRAP: {len(s.get('agents',[]))}/{POPULATION_SIZE} agents; created={created}; complete={complete}")
    return complete

def load():
    try:
      s=json.loads(STATE_FILE.read_text())
      if s.get("schema_version") in (5,6):
        if s.get("schema_version")==5: s["schema_version"]=6
        s.setdefault("agents",[])
        for a in s["agents"]:
            a.setdefault("main_character",False); a.setdefault("protected_identity",False); a.setdefault("memory_budget_mb",1)
            a.setdefault("brain",{}).setdefault("self_model",{}); a["brain"].setdefault("plans",[]); a["brain"].setdefault("critic_notes",[])
        used={a.get("name") for a in s["agents"] if a.get("name")}; _ensure_cactus(s,used)
        s["alive_count"]=sum(1 for a in s["agents"] if a.get("permanent_status")=="alive")
        s["bootstrap_complete"]=len(s["agents"])>=max(1,POPULATION_SIZE)
        return s
    except Exception:
      return fresh_state()

def save(s): STATE_FILE.write_text(json.dumps(s,indent=2,ensure_ascii=False))

def load_opps():
    try: return json.loads((ROOT/"opportunities.json").read_text()).get("opportunities",[])
    except Exception: return []

def dispatch(agents,opps,day):
    # Everyone can compete for the whole discovered pool; no role whitelist.
    ranked=sorted(opps,key=lambda x:float(x.get("score",0)),reverse=True)
    for a in agents:
      if a.get("permanent_status") != "alive": continue
      if not ranked: continue
      choices=ranked[:min(100,len(ranked))]
      try:
        import agent_self_modification
        bonus=agent_self_modification.score_bonus(a,{"skill_total":sum(float(v or 0) for v in a.get("skills",{}).values()),"recent_success":float(a.get("wins",0) or 0)})
      except Exception:
        bonus=0.0
      fit=max(choices,key=lambda x:float(x.get("score",0))+bonus+random.random()*10)
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
      "generation":a.get("generation",0),"main_character":a.get("main_character",False)} for i,a in enumerate(arr[:50],1)]


def clone_champion(s,today):
    r=rules().get("owner_rules",{})
    if not r.get("champion_cloning_enabled",True) or today<=0 or len(s["agents"])>=CLONE_CAP: return None
    if not s["agents"]: return None
    champ=max(s["agents"],key=lambda a:(a.get("own_verified_revenue",0),sum(a["skills"].values()),a.get("wins",0)))
    used={a["name"] for a in s["agents"]}
    c=new_agent(used,champ)
    try:
      import evolution_genetics
      evolution_genetics.inherit(champ, c)
    except Exception:
      pass
    c["parent"]=champ["id"]
    s["agents"].append(c); s["clone_count"]=s.get("clone_count",0)+1
    return c

CURRENT_DAY=0
def main():
    global CURRENT_DAY
    s=load()
    if len(s.get("agents",[])) < max(1, POPULATION_SIZE):
        created,complete=_bootstrap_population(s); save(s)
        print(f"POPULATION BOOTSTRAP: {len(s.get('agents',[]))}/{POPULATION_SIZE} agents; created={created}; complete={complete}")
        return 0
    s["day"]+=1; CURRENT_DAY=s["day"]
    sync_from_state(s)
    opps=load_opps()
    # The world itself evolves before agents choose work. This changes demand,
    # competition, resource pressure and opportunity conditions from observed
    # activity without inventing revenue or customers.
    try:
      import environment_engine
      world=environment_engine.evolve_world(s)
      opps=load_opps()
      print("WORLD:", {k: round(v,3) for k,v in world.get("conditions",{}).items()})
    except Exception as e:
      print("ENVIRONMENT ENGINE ERROR:", e)
    try:
      import opportunity_intelligence
      opportunity_intelligence.run(opps)
      opps=load_opps()
    except Exception as e:
      print("OPPORTUNITY INTELLIGENCE ERROR:", e)
    try:
      import adversarial_guard
      guard=adversarial_guard.run(s)
      if guard.get("status") != "clean":
        print("ADVERSARIAL GUARD QUARANTINE:", len(guard.get("findings",[])))
    except Exception as e:
      print("ADVERSARIAL GUARD ERROR:", e)
    dispatch(s["agents"],opps,CURRENT_DAY)
    # Optional recursive agent hierarchy: an agent may choose to create sub-agents.
    # Sub-agents make their own decisions and may later create their own sub-agents.
    try:
      import agent_hierarchy
      created=agent_hierarchy.run(s, max_new=int(os.getenv("SUBAGENT_BATCH", "50")))
      if created: print(f"SUB-AGENTS: {len(created)} created this cycle")
    except Exception as e:
      print("AGENT HIERARCHY ERROR:", e)
    # Meta-evolution: diagnose, score, plan, learn, recover, and build reputation.
    try:
      import evolution_genetics
      evolution_genetics.run(s)
    except Exception as e:
      print("GENETICS ERROR:", e)
    try:
      import agent_skill_engine
      agent_skill_engine.run(s)
    except Exception as e:
      print("SKILL ENGINE ERROR:", e)
    try:
      import evolution_system
      evolution_system.run(s, opps, CURRENT_DAY)
    except Exception as e:
      print("EVOLUTION SYSTEM ERROR:", e)
    try:
      import agent_intelligence
      agent_intelligence.run(s, opps, CURRENT_DAY)
    except Exception as e:
      print("INTELLIGENCE ERROR:", e)
    try:
      import experiment_lab
      experiment_lab.run(s)
    except Exception as e:
      print("EXPERIMENT LAB ERROR:", e)
    try:
      import agent_marketplace
      agent_marketplace.run(s)
    except Exception as e:
      print("MARKETPLACE ERROR:", e)
    try:
      import agent_self_modification
      edits=agent_self_modification.run(s, max_agents=int(os.getenv("SELF_MOD_BATCH", "100")))
      accepted=sum(1 for x in edits if x.get("status")=="accepted")
      print(f"SELF-MODIFICATION: {accepted}/{len(edits)} agent code edits accepted this cycle")
    except Exception as e:
      print("SELF-MODIFICATION ERROR:", e)
    try:
      import team_engine
      team_engine.run(s)
    except Exception as e:
      print("TEAM ENGINE ERROR:", e)
    try:
      import multitask_engine
      multitask_engine.run(s)
    except Exception as e:
      print("MULTITASK ENGINE ERROR:", e)
    # Work execution is a separate hard-gated stage. The simulator only consumes
    # completed-work records; discovery/selection alone never counts as completion.
    try:
      import work_executor
      work_executor.run_cycle(s, CURRENT_DAY)
    except Exception as e:
      print("WORK EXECUTION ERROR:", e)
    try:
      import business_ecosystem
      business_ecosystem.run(s, opps)
    except Exception as e:
      print("BUSINESS ECOSYSTEM ERROR:", e)
    try:
      import economy_engine
      economy_engine.run(s)
    except Exception as e:
      print("ECONOMY ENGINE ERROR:", e)
    try:
      import agent_superintelligence
      agent_superintelligence.run(s, opps, CURRENT_DAY)
    except Exception as e:
      print("SUPERINTELLIGENCE ERROR:", e)
    try:
      import business_market_engine
      business_market_engine.run(s, opps)
    except Exception as e:
      print("BUSINESS MARKET ENGINE ERROR:", e)
    try:
      import economy_intelligence
      economy_intelligence.run(s)
    except Exception as e:
      print("ECONOMY INTELLIGENCE ERROR:", e)
    try:
      import cactus_needle_core
      cactus_needle_core.run(s)
    except Exception as e:
      print("CACTUS NEEDLE CORE ERROR:", e)
    try:
      import farm_dashboard
      farm_dashboard.main()
    except Exception as e:
      print("DASHBOARD ERROR:", e)
    try:
      import recovery_manager
      recovery_manager.run(s, ROOT)
    except Exception as e:
      print("RECOVERY ERROR:", e)
    payments=apply_verified_payments(s)
    # Work growth is tied to attempts, not free simulated income.
    for a in s["agents"]:
      a["days_active"]+=1
      # Each cycle produces an activity record. A run is not called successful merely
      # because an opportunity was found; success requires an observable result.
      top_skill=max(a.get("skills",{}).values() or [0])
      completed=int(a.get("completed_work",0))
      successful=completed>0
      record_agent(a,"WORK_RUN",f"Completed {completed} work item(s); unfinished work remains queued until completed.",quality=min(100,20+top_skill),successful=successful,work=completed)
      if completed:
        for _ in range(min(3,completed+1)):
          k=random.choice(SKILLS); a["skills"][k]=round(min(100,a["skills"][k]+random.uniform(.2,1.5)),2)
          a["brain"]["lessons"].append({"day":s["day"],"skill":k,"source":"work_attempt"})
          a["brain"]["lessons"]=a["brain"]["lessons"][-50:]
    for a in s["agents"]:
      record_snapshot(a, s["day"])
    rank(s)
    try:
      import evolution_lab_max
      evolution_lab_max.run(s)
    except Exception as e:
      print("MAX EVOLUTION LAB ERROR:", e)
    try:
      import lineage_replay
      lineage_replay.record(s, label="pre-survival")
    except Exception as e:
      print("LINEAGE REPLAY ERROR:", e)
    try:
      import evolution_system
      evolution_system.tournament(s, CURRENT_DAY)
    except Exception as e:
      print("TOURNAMENT ERROR:", e)
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
    prepared=sum(int(a.get("completed_work",0)) for a in s["agents"])
    s["completed_work_total"]=prepared
    s["unfinished_work_total"]=sum(len(a.get("active_work",[])) for a in s["agents"])
    s,deaths=apply_survival(s,len(opps),prepared,verified_today)
    save(s)
    print(f"DAY {s['day']} | alive={len(s['agents'])} | permanent_deaths={s.get('dead_count',0)} | opportunities={len(opps)} | verified_today_by_currency={s.get('currency_balances',{})}")
    if s.get("leaderboard"): print("NUMBER ONE:",s["leaderboard"][0])
    if clone: print("CHAMPION CLONED:",clone["name"],"parent=",clone["parent"])
    if deaths: print("PERMANENT DEATHS:",", ".join(x["name"] for x in deaths))
if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--bootstrap-only",action="store_true"); args=parser.parse_args()
    if args.bootstrap_only: raise SystemExit(0 if bootstrap_only() else 0)
    main()
