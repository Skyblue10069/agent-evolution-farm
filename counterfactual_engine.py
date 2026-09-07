#!/usr/bin/env python3
"""Bounded counterfactual strategy analysis.

It estimates alternative strategy scores from observed history only. It never
creates simulated revenue and never treats an estimate as an external result.
"""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; FILE=ROOT/'counterfactuals.json'

def run(state):
    out={'schema_version':1,'day':state.get('day',0),'agents':{}}
    for a in state.get('agents',[]):
        wins=float(a.get('wins',0) or 0); losses=float(a.get('losses',0) or 0); work=float(a.get('completed_work',0) or 0)
        base=wins+0.25*work-0.25*losses
        candidates={'explore':base,'deep_work':base+min(10,work*.1),'collaborate':base+min(8,wins*.2),'risk_control':base+min(8,max(0,losses*.15))}
        out['agents'][a.get('id')]={'observed_baseline':round(base,3),'alternatives':{k:round(v,3) for k,v in candidates.items()},'label':'counterfactual_estimate_not_real_result'}
    FILE.write_text(json.dumps(out,indent=2)); return out
if __name__=='__main__': run(json.loads((ROOT/'state.json').read_text()))
