#!/usr/bin/env python3
"""Deterministic shard execution plan for large populations.
This planner intentionally does not mutate shared state concurrently. It emits
stable shards and a merge manifest so future runners can process isolated work.
"""
from __future__ import annotations
import argparse,json,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def build(state,batch=500,shards=0):
    agents=state.get('agents',[]); n=len(agents); shards=shards or max(1,math.ceil(n/max(1,batch)))
    groups=[[] for _ in range(shards)]
    for i,a in enumerate(agents): groups[i%shards].append(a.get('id'))
    manifest={'schema_version':1,'population':n,'batch_size':batch,'shards':[],'merge_policy':'stable_id_order; verified ledgers are source of truth'}
    for i,g in enumerate(groups):
        ids=g[:batch]; payload={'shard':i,'agent_ids':ids,'count':len(ids)}; payload['digest']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(); manifest['shards'].append(payload)
    (ROOT/'distributed_manifest.json').write_text(json.dumps(manifest,indent=2)); return manifest

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--batch-size',type=int,default=500); ap.add_argument('--shards',type=int,default=0); args=ap.parse_args(); s=json.loads((ROOT/'state.json').read_text()); m=build(s,args.batch_size,args.shards); print(f'DISTRIBUTED PLAN: population={m["population"]} shards={len(m["shards"])} batch={m["batch_size"]}')
if __name__=='__main__': main()
