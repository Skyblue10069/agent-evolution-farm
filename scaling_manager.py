#!/usr/bin/env python3
"""Scalable shard planner for large agent populations.

This is a planning/inspection utility. It does not concurrently mutate the
same state file, avoiding race conditions in GitHub Actions.
"""
import argparse, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--shards',type=int,default=0); ap.add_argument('--batch-size',type=int,default=500); args=ap.parse_args()
    s=json.loads((ROOT/'state.json').read_text())
    agents=s.get('agents',[]); n=len(agents)
    shards=args.shards or max(1,math.ceil(n/args.batch_size))
    groups=[[] for _ in range(shards)]
    for i,a in enumerate(agents): groups[i%shards].append(a.get('id'))
    out={'population':n,'shards':shards,'batch_size':args.batch_size,'groups':[{'shard':i,'count':len(g),'agent_ids':g[:args.batch_size]} for i,g in enumerate(groups)]}
    (ROOT/'scaling_plan.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(f'SCALING PLAN: population={n} shards={shards} batch_size={args.batch_size}')
if __name__=='__main__': main()
