#!/usr/bin/env python3
"""Evidence-driven max evolution layer: strategy selection and rollback journal."""
from __future__ import annotations
import json,hashlib,random
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'evolution_lab_max.json'

def load():
    try:return json.loads(STATE.read_text())
    except Exception:return {'schema_version':1,'strategies':{},'events':[],'generation':0}

def run(s):
    d=load(); d['generation']=int(s.get('day',0));
    for a in s.get('agents',[]):
        aid=a.get('id'); success=float(a.get('wins',0) or 0); failure=float(a.get('losses',0) or 0); work=float(a.get('completed_work',0) or 0)
        traits=a.get('traits',{}) or {}
        candidates={
          'explore':float(traits.get('curiosity',50))+float(traits.get('creativity',50)),
          'deep_work':float(traits.get('focus',50))+float(traits.get('patience',50))+work,
          'collaborate':float(traits.get('cooperation',50))+float(a.get('wins',0) or 0),
          'risk_control':100-float(traits.get('risk_tolerance',50))+failure
        }
        chosen=max(candidates,key=candidates.get)
        rec=d['strategies'].setdefault(aid,{'counts':{},'outcomes':{}}); rec['counts'][chosen]=rec['counts'].get(chosen,0)+1; rec['outcomes'][chosen]=round(rec['outcomes'].get(chosen,0)+success-max(0,failure*.25),3)
        a.setdefault('brain',{}).setdefault('lessons',[]).append({'day':s.get('day',0),'strategy':chosen,'evidence':'observed_outcomes_only'})
        a['brain']['lessons']=a['brain']['lessons'][-50:]
    event={'day':s.get('day',0),'agents':len(s.get('agents',[])),'created_at':datetime.now(timezone.utc).isoformat()}
    d['events']=(d.get('events',[])[-499:]+[event]); d['digest']=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest(); STATE.write_text(json.dumps(d,indent=2))
    return d

def main():
    s=json.loads((ROOT/'state.json').read_text()); r=run(s); print(f'MAX EVOLUTION LAB: generation={r["generation"]} strategies={len(r["strategies"])} digest={r["digest"][:12]}')
if __name__=='__main__': main()
