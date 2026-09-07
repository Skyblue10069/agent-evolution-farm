#!/usr/bin/env python3
"""Farm immune system: detect impossible/suspicious state transitions and quarantine findings."""
from __future__ import annotations
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent; FILE=ROOT/'immune_system.json'

def run(state):
    findings=[]
    seen=set()
    for a in state.get('agents',[]):
        aid=a.get('id')
        if not aid or aid in seen: findings.append({'type':'duplicate_or_missing_id','agent_id':aid}); continue
        seen.add(aid)
        for k,v in (a.get('skills',{}) or {}).items():
            try:
                if not math.isfinite(float(v)) or float(v)<0 or float(v)>100: findings.append({'type':'invalid_skill','agent_id':aid,'skill':k,'value':v})
            except Exception: findings.append({'type':'non_numeric_skill','agent_id':aid,'skill':k})
        if float(a.get('cash_verified',0) or 0)<0: findings.append({'type':'negative_verified_cash','agent_id':aid})
    d={'schema_version':1,'status':'clean' if not findings else 'quarantine','day':state.get('day',0),'findings':findings[:500]}
    FILE.write_text(json.dumps(d,indent=2)); return d
if __name__=='__main__': print(run(json.loads((ROOT/'state.json').read_text())))
