"""Optional recursive agent hierarchy.

An agent can choose to create a sub-agent when its own decision state indicates
that delegation would be useful. A child starts without money and develops its
own skills. Children can independently choose to create children, producing an
arbitrarily deep hierarchy until the configured farm resource cap is reached.
"""
from __future__ import annotations
import json, random
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE_FILE=ROOT/"agent_hierarchy_state.json"


def _load():
    try: return json.loads(STATE_FILE.read_text())
    except Exception: return {"schema_version":1,"created_total":0,"events":[]}


def _save(x):
    STATE_FILE.write_text(json.dumps(x,indent=2))


def _new_child(parent, used, depth):
    # Import the simulator's constructor without duplicating agent schema.
    from simulate import new_agent
    child=new_agent(used)
    try:
        from evolution_genetics import inherit
        inherit(parent, child)
    except Exception:
        pass
    child["parent"]=parent["id"]
    h=child.setdefault("hierarchy",{})
    h.update({"parent_id":parent["id"],"children":[],"spawned_subagents":0,"wants_subagents":False,"depth":depth})
    # A child starts with no cash/customer ownership. It inherits only lineage metadata.
    child["skills"]={k:0.0 for k in child.get("skills",{})}
    child["cash_verified"]=0.0
    child["own_verified_revenue"]=0.0
    child["earnings_by_currency"]={}
    child["own_verified_revenue_by_currency"]={}
    return child


def _wants(parent, day, rng):
    h=parent.setdefault("hierarchy",{})
    # Agents are not forced to spawn. They choose based on a learned/delegation signal.
    # The signal grows from leadership/strategy/project-management skill and recent wins,
    # while a small exploration factor lets different agents discover delegation naturally.
    skills=parent.get("skills",{})
    leadership=float(skills.get("leadership",0) or 0)
    strategy=float(skills.get("strategy",0) or 0)
    pm=float(skills.get("project_management",0) or 0)
    wins=float(parent.get("wins",0) or 0)
    delegation_score=(leadership*0.35+strategy*0.2+pm*0.25+min(20,wins)*0.2)/100
    if h.get("wants_subagents") is True:
        return True
    if h.get("wants_subagents") is False and h.get("decision_count",0)>0:
        # Once an agent has explicitly declined, it may reconsider later as it evolves.
        return delegation_score > 0.72 and rng.random() < 0.15
    return delegation_score > 0.35 and rng.random() < 0.18


def run(state, max_new=50):
    agents=state.get("agents",[])
    cap=max(len(agents), int(__import__('os').getenv("SUBAGENT_CAP","20000")))
    remaining=max(0, min(int(max_new), cap-len(agents)))
    if remaining<=0: return []
    day=int(state.get("day",0) or 0)
    rng=random.Random(f"hierarchy:{day}")
    used={a.get("name") for a in agents}
    eligible=[a for a in agents if a.get("permanent_status")=="alive"]
    rng.shuffle(eligible)
    meta=_load(); created=[]
    for parent in eligible:
        if len(created)>=remaining: break
        h=parent.setdefault("hierarchy",{"parent_id":None,"children":[],"spawned_subagents":0,"wants_subagents":False,"depth":0})
        h["decision_count"]=int(h.get("decision_count",0))+1
        if not _wants(parent,day,rng):
            h["last_decision"]="declined"
            continue
        h["wants_subagents"]=True
        child=_new_child(parent,used,int(h.get("depth",0))+1)
        agents.append(child)
        h.setdefault("children",[]).append(child["id"])
        h["spawned_subagents"]=int(h.get("spawned_subagents",0))+1
        h["last_decision"]="spawned"
        child.setdefault("brain",{}).setdefault("goals",[]).append({"day":day,"type":"subagent_spawn","parent_id":parent["id"]})
        created.append(child)
    if created:
        meta["created_total"]=int(meta.get("created_total",0))+len(created)
        meta.setdefault("events",[]).append({"day":day,"created":len(created),"total_agents":len(agents)})
        meta["events"]=meta["events"][-1000:]
        _save(meta)
        state["alive_count"]=sum(1 for a in agents if a.get("permanent_status")=="alive")
        state["hierarchy"]={"total_agents":len(agents),"root_agents":sum(1 for a in agents if not a.get("hierarchy",{}).get("parent_id")),"max_depth":max((int(a.get("hierarchy",{}).get("depth",0)) for a in agents),default=0),"subagent_created_total":meta["created_total"]}
    return created
