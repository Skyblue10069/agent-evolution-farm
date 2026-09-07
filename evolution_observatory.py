#!/usr/bin/env python3
"""Read-only aggregate observatory for the owner dashboard."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; FILE=ROOT/'evolution_observatory.json'

def run(state):
    agents=state.get('agents',[]); alive=[a for a in agents if a.get('permanent_status')=='alive']; dead=len(agents)-len(alive)
    skills={}
    for a in agents:
        for k,v in (a.get('skills',{}) or {}).items(): skills[k]=skills.get(k,0)+float(v or 0)
    top=sorted(agents,key=lambda a:(float(a.get('own_verified_revenue',0) or 0),float(a.get('wins',0) or 0)),reverse=True)[:10]
    d={'schema_version':1,'day':state.get('day',0),'population':len(agents),'alive':len(alive),'dead':dead,'verified_revenue':state.get('verified_revenue',0),'average_skill_total':round(sum(sum(float(v or 0) for v in (a.get('skills',{}) or {}).values()) for a in agents)/max(1,len(agents)),3),'top_agents':[{'id':a.get('id'),'name':a.get('name'),'revenue':a.get('own_verified_revenue',0),'wins':a.get('wins',0),'generation':a.get('generation',0)} for a in top],'skill_totals':{k:round(v,2) for k,v in skills.items()}}
    FILE.write_text(json.dumps(d,indent=2)); return d
if __name__=='__main__': run(json.loads((ROOT/'state.json').read_text()))
