#!/usr/bin/env python3
"""Immutable generation snapshots with bounded retention and content hashes."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent; DIR=ROOT/'generations'; DIR.mkdir(exist_ok=True); INDEX=ROOT/'generations_index.json'
def record(state):
    compact=[{'id':a.get('id'),'generation':a.get('generation',0),'alive':a.get('permanent_status')=='alive','wins':a.get('wins',0),'losses':a.get('losses',0),'work':a.get('completed_work',0),'skills':a.get('skills',{})} for a in state.get('agents',[])]
    payload={'schema_version':1,'day':state.get('day',0),'population':len(compact),'agents':compact,'created_at':datetime.now(timezone.utc).isoformat()}
    payload['digest']=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    path=DIR/f"generation-{int(state.get('day',0)):08d}.json"
    if path.exists():
        # Never overwrite an existing generation snapshot.
        path=DIR/f"generation-{int(state.get('day',0)):08d}-{payload['digest'][:12]}.json"
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False))
    idx={'schema_version':1,'generations':[]}
    if INDEX.exists():
        try: idx=json.loads(INDEX.read_text())
        except Exception: pass
    idx['generations']=(idx.get('generations',[])[-99:]+[{'day':payload['day'],'file':str(path.relative_to(ROOT)),'digest':payload['digest']}])
    INDEX.write_text(json.dumps(idx,indent=2)); return payload
if __name__=='__main__': record(json.loads((ROOT/'state.json').read_text()))
