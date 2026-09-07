#!/usr/bin/env python3
"""Persistent lineage, generation snapshots, and replay metadata.

Snapshots are compact JSON and contain no secrets. They explain *why* agents
won/lost without replaying external side effects.
"""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DIR=ROOT/'lineage_replays'; DIR.mkdir(exist_ok=True)
INDEX=ROOT/'lineage_index.json'

def _load():
    try: return json.loads(INDEX.read_text())
    except Exception: return {'schema_version':1,'replays':[]}

def _digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def record(state, label='cycle'):
    agents=state.get('agents',[])
    ranked=sorted(agents,key=lambda a:(float(a.get('own_verified_revenue',0) or 0),float(a.get('wins',0) or 0),sum(float(v or 0) for v in a.get('skills',{}).values())),reverse=True)
    compact=[]
    for a in ranked[:100]:
        compact.append({'id':a.get('id'),'name':a.get('name'),'parent':a.get('parent'),'generation':a.get('generation',0),'alive':a.get('permanent_status')=='alive','revenue_xaf':a.get('own_verified_revenue',0),'wins':a.get('wins',0),'losses':a.get('losses',0),'completed_work':a.get('completed_work',0),'skill_total':round(sum(float(v or 0) for v in a.get('skills',{}).values()),2),'traits':a.get('traits',{}),'children':len(a.get('hierarchy',{}).get('children',[]))})
    payload={'schema_version':1,'day':state.get('day',0),'population':len(agents),'alive':sum(1 for a in agents if a.get('permanent_status')=='alive'),'dead':sum(1 for a in agents if a.get('permanent_status')!='alive'),'verified_revenue':state.get('verified_revenue',0),'top_agents':compact}
    payload['digest']=_digest(payload)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path=DIR/f'{label}-day-{int(state.get("day",0))}-{stamp}.json'
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False))
    idx=_load(); idx['replays']=idx.get('replays',[])[-199:]+[{'day':payload['day'],'file':str(path.relative_to(ROOT)),'digest':payload['digest'],'created_at':datetime.now(timezone.utc).isoformat()}]
    INDEX.write_text(json.dumps(idx,indent=2))
    return payload

def main():
    state=json.loads((ROOT/'state.json').read_text())
    p=record(state)
    print(f'LINEAGE REPLAY: day={p["day"]} population={p["population"]} digest={p["digest"][:12]}')
if __name__=='__main__': main()
