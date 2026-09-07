#!/usr/bin/env python3
"""Bounded multi-step strategy trees with rollback-friendly telemetry."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; FILE=ROOT/'strategy_tree.json'
def load():
    try:return json.loads(FILE.read_text())
    except Exception:return {'schema_version':1,'agents':{}}
def run(state):
    d=load()
    for a in state.get('agents',[]):
        aid=a.get('id'); traits=a.get('traits',{}) or {}; risk=float(traits.get('risk_tolerance',50) or 50)
        branches=['discover','validate','prepare','deliver']
        branches += ['experiment'] if risk>65 else (['risk_check'] if risk<35 else [])
        d['agents'][aid]={'day':state.get('day',0),'depth':min(6,len(branches)),'branches':branches,'status':'planned','evidence_policy':'observed_results_only'}
    FILE.write_text(json.dumps(d,indent=2)); return d
if __name__=='__main__': run(json.loads((ROOT/'state.json').read_text()))
