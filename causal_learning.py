#!/usr/bin/env python3
"""Causal-learning telemetry from observed outcomes.
This is deliberately conservative: it records associations/contrasts and does
not claim causality from uncontrolled observations. Controlled experiments can
promote hypotheses later.
"""
from __future__ import annotations
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent; FILE=ROOT/'causal_learning.json'

def load():
    try:return json.loads(FILE.read_text())
    except Exception:return {'schema_version':1,'features':{},'comparisons':[]}

def run(state):
    d=load(); rows=[]
    for a in state.get('agents',[]):
        skills=a.get('skills',{}) or {}; traits=a.get('traits',{}) or {}
        outcome=float(a.get('wins',0) or 0)+0.25*float(a.get('completed_work',0) or 0)-0.25*float(a.get('losses',0) or 0)
        rows.append((a.get('id'),outcome,float(traits.get('discipline',50) or 50),sum(float(v or 0) for v in skills.values())))
    def corr(idx):
        vals=[r[idx] for r in rows]; outs=[r[1] for r in rows]
        if len(vals)<2:return 0.0
        mx=sum(vals)/len(vals); my=sum(outs)/len(outs); num=sum((x-mx)*(y-my) for x,y in zip(vals,outs)); den=math.sqrt(sum((x-mx)**2 for x in vals)*sum((y-my)**2 for y in outs))
        return num/den if den else 0.0
    d['features']['discipline_vs_observed_outcome']=round(corr(2),4); d['features']['skill_total_vs_observed_outcome']=round(corr(3),4)
    d['comparisons']=(d.get('comparisons',[])[-199:]+[{'day':state.get('day',0),'sample_size':len(rows),'note':'observational; not proof of causality'}])
    FILE.write_text(json.dumps(d,indent=2)); return d
if __name__=='__main__': run(json.loads((ROOT/'state.json').read_text()))
