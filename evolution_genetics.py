"""Safe evolutionary genetics for agent traits and champion inheritance."""
import random
TRAITS=("creativity","patience","risk_tolerance","learning_rate","negotiation","research_depth","cooperation","failure_recovery")

def ensure(a):
    traits=a.setdefault("traits",{})
    for t in TRAITS:
        traits.setdefault(t, round(random.uniform(0,1),3))
    a.setdefault("genome", {"traits":dict(traits),"mutations":0,"lineage":[]})
    return a

def inherit(parent, child):
    ensure(parent); ensure(child)
    for t in TRAITS:
        base=float(parent["traits"].get(t,.5))
        child["traits"][t]=round(max(0,min(1,base+random.uniform(-.05,.05))),3)
    child["genome"]={"traits":dict(child["traits"]),"mutations":sum(1 for t in TRAITS if child["traits"][t]!=parent["traits"].get(t)),"lineage":(parent.get("genome",{}).get("lineage",[])+[parent.get("id")])[-10:]}

def run(s):
    for a in s.get("agents",[]):
        ensure(a)
    s["evolution_genetics"]={"traits":list(TRAITS),"generation_max":max((a.get("generation",0) for a in s.get("agents",[])),default=0)}
