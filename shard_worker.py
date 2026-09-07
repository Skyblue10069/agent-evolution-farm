#!/usr/bin/env python3
"""Read-only shard worker for MAX+ coordinator.
Never mutates canonical state. Produces one isolated result JSON."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

def digest(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-dir',required=True); ap.add_argument('--shard',type=int,required=True); args=ap.parse_args()
    run=Path(args.run_dir); manifest=json.loads((run/'manifest.json').read_text()); state=json.loads((Path(__file__).resolve().parent/'state.json').read_text())
    spec=next(x for x in manifest['shards'] if x['shard']==args.shard); wanted=set(spec['agent_ids']); updates=[]
    for a in state.get('agents',[]):
        if a.get('id') not in wanted: continue
        skills=a.get('skills',{}) or {}; total=sum(float(v or 0) for v in skills.values()); wins=float(a.get('wins',0) or 0); losses=float(a.get('losses',0) or 0)
        traits=a.get('traits',{}) or {}; curiosity=float(traits.get('curiosity',50) or 50); discipline=float(traits.get('discipline',50) or 50)
        score=max(0.0,min(100.0,50 + total/20 + wins*0.5 - losses*0.25 + curiosity*0.1 + discipline*0.1))
        updates.append({'agent_id':a['id'],'coordinator':{'decision_score':round(score,3),'last_coordinated_day':manifest['day'],'shard':args.shard}})
    result={'schema_version':1,'run_id':manifest['run_id'],'shard':args.shard,'agent_updates':updates,'created_at':datetime.now(timezone.utc).isoformat()}
    result['digest']=digest(result); (run/f'result-{args.shard:05d}.json').write_text(json.dumps(result,indent=2))
    print(f"SHARD {args.shard}: {len(updates)} agents")
if __name__=='__main__': main()
