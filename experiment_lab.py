"""Bounded A/B experimentation. Experiments measure existing outcomes only; no fake revenue."""
import random

def run(s):
    results=s.setdefault("experiments",[])
    alive=[a for a in s.get("agents",[]) if a.get("permanent_status")=="alive"]
    sample=alive[:min(500,len(alive))]
    for a in sample:
        traits=a.get("traits",{})
        variant="A" if random.random()<.5 else "B"
        signal=(sum(float(v) for v in traits.values())/max(1,len(traits))) + random.uniform(-.05,.05)
        a.setdefault("brain",{}).setdefault("experiments",[]).append({"day":s.get("day",0),"variant":variant,"observed_signal":round(signal,4)})
    results.append({"day":s.get("day",0),"sample":len(sample),"variants":["A","B"],"status":"observational"})
    s["experiments"]=results[-30:]
