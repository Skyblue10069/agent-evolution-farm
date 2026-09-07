#!/usr/bin/env python3
"""MAX+ coordinator: deterministic, isolated shard orchestration.

Workers only produce shard-local decision/telemetry files. The coordinator is
solely responsible for merging those results into the canonical state. No
worker is allowed to mutate state.json, payment ledgers, or the git checkout.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state.json"
RUNS = ROOT / "coordinator_runs"
LOCK = ROOT / "coordinator.lock"
RUNS.mkdir(exist_ok=True)


def now(): return datetime.now(timezone.utc).isoformat()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def load_state(): return json.loads(STATE.read_text())

def acquire_lock():
    if LOCK.exists():
        try:
            age = time.time() - LOCK.stat().st_mtime
            if age < 3600:
                raise RuntimeError("coordinator lock exists; refusing concurrent canonical-state orchestration")
        except FileNotFoundError:
            pass
    LOCK.write_text(json.dumps({"pid": os.getpid(), "started_at": now()}))

def release_lock():
    try: LOCK.unlink()
    except FileNotFoundError: pass

def plan(state, batch):
    agents = state.get("agents", [])
    groups = [agents[i:i+batch] for i in range(0, len(agents), batch)]
    return [{"shard": i, "agent_ids": [a.get("id") for a in g], "count": len(g)} for i, g in enumerate(groups)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=int(os.getenv("COORDINATOR_BATCH_SIZE", "500")))
    ap.add_argument("--max-shards", type=int, default=int(os.getenv("COORDINATOR_MAX_SHARDS", "0")))
    ap.add_argument("--workers", type=int, default=int(os.getenv("COORDINATOR_WORKERS", "1")))
    args=ap.parse_args()
    if args.batch_size < 1 or args.workers < 1: raise SystemExit("batch-size/workers must be positive")
    acquire_lock()
    try:
        state=load_state(); cycle=int(state.get("day",0)); run_id=f"day-{cycle}-{int(time.time())}"
        run_dir=RUNS/run_id; run_dir.mkdir(parents=True, exist_ok=False)
        shards=plan(state,args.batch_size)
        if args.max_shards>0: shards=shards[:args.max_shards]
        manifest={"schema_version":2,"run_id":run_id,"day":cycle,"population":len(state.get("agents",[])),"batch_size":args.batch_size,"requested_workers":args.workers,"shards":shards,"merge_policy":"coordinator-only canonical merge; shard outputs are isolated and deterministic"}
        manifest["digest"]=digest(manifest); (run_dir/"manifest.json").write_text(json.dumps(manifest,indent=2))
        procs=[]
        for s in shards:
            cmd=[sys.executable,"shard_worker.py","--run-dir",str(run_dir),"--shard",str(s["shard"])]
            procs.append(subprocess.Popen(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
            if len(procs)>=args.workers:
                p=procs.pop(0); out,err=p.communicate()
                if p.returncode: raise RuntimeError(f"shard failed: {err[-2000:]}")
        for p in procs:
            out,err=p.communicate()
            if p.returncode: raise RuntimeError(f"shard failed: {err[-2000:]}")
        result_files=sorted(run_dir.glob("result-*.json"))
        if len(result_files)!=len(shards): raise RuntimeError(f"expected {len(shards)} shard results, found {len(result_files)}")
        results=[json.loads(p.read_text()) for p in result_files]
        ids=[x["agent_id"] for r in results for x in r.get("agent_updates",[])]
        if len(ids)!=len(set(ids)): raise RuntimeError("duplicate agent ownership detected during merge")
        updates={x["agent_id"]:x for r in results for x in r.get("agent_updates",[])}
        changed=0
        for a in state.get("agents",[]):
            u=updates.get(a.get("id"))
            if not u: continue
            a.setdefault("coordinator",{}).update(u.get("coordinator",{})); changed+=1
        merged={"schema_version":1,"run_id":run_id,"day":cycle,"shards":len(results),"agents_merged":changed,"result_digests":[r.get("digest") for r in results],"created_at":now()}
        merged["digest"]=digest(merged); (run_dir/"merge.json").write_text(json.dumps(merged,indent=2))
        STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False))
        (ROOT/"coordinator_latest.json").write_text(json.dumps(merged,indent=2))
        print(f"COORDINATOR: day={cycle} shards={len(results)} agents_merged={changed} digest={merged['digest'][:12]}")
    finally:
        release_lock()

if __name__=='__main__': main()
