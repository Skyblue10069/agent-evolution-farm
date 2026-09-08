#!/usr/bin/env python3
"""Reliable GitHub-first Agent Evolution cycle orchestrator.

Runs the farm's independent stages with per-stage timeouts, checkpoints, and
an append-only audit log. It does not invent external work, customers, or
payments. External actions remain subject to each provider's permissions.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "orchestrator_state.json"
AUDIT = ROOT / "orchestrator_audit.jsonl"

STAGES = [
    ("accounts", [sys.executable, "agent_accounts.py"], 60),
    ("discovery", [sys.executable, "worldwide_discovery.py", "--max-results", "6", "--max-opportunities", "1000", "--time-limit-seconds", "540", "--max-queries", "16"], 570),
    ("opportunity_intelligence", [sys.executable, "opportunity_intelligence.py"], 120),
    ("adversarial_guard", [sys.executable, "adversarial_guard.py"], 120),
    ("environment", [sys.executable, "environment_engine.py"], 120),
    ("internet_capability", [sys.executable, "internet_agent.py"], 120),
    ("brain", [sys.executable, "autonomous_brain.py"], 180),
    ("intelligence", [sys.executable, "agent_intelligence.py"], 180),
    ("self_modification", [sys.executable, "agent_self_modification.py"], 180),
    ("work_prepare", [sys.executable, "work_preparer.py", "--limit", "500"], 180),
    ("work_execute", [sys.executable, "work_executor.py"], 300),
    ("business_factory", [sys.executable, "business_factory.py"], 180),
    ("business_evolution", [sys.executable, "business_evolution.py"], 180),
    ("business_ecosystem", [sys.executable, "business_ecosystem.py"], 180),
    ("currency_tests", [sys.executable, "multi_currency_tests.py"], 120),
    ("economy", [sys.executable, "economy_engine.py"], 180),
    ("currency_ledger", [sys.executable, "currency_ledger.py"], 180),
    ("verified_payments", [sys.executable, "payout_router.py"], 180),
    ("survival", [sys.executable, "simulate.py"], 1800),
    ("coordinator", [sys.executable, "coordinator.py", "--batch-size", "500", "--workers", "4"], 180),
    ("causal_learning", [sys.executable, "causal_learning.py"], 120),
    ("counterfactual_engine", [sys.executable, "counterfactual_engine.py"], 120),
    ("strategy_tree", [sys.executable, "strategy_tree.py"], 120),
    ("immune_system", [sys.executable, "immune_system.py"], 120),
    ("generation_store", [sys.executable, "generation_store.py"], 180),
    ("improvement_upgrade", [sys.executable, "evolution_upgrade.py"], 240),
    ("evolution_lab_max", [sys.executable, "evolution_lab_max.py"], 180),
    ("lineage_replay", [sys.executable, "lineage_replay.py"], 120),
    ("evolution_observatory", [sys.executable, "evolution_observatory.py"], 120),
    ("dashboard", [sys.executable, "farm_dashboard.py"], 60),
    ("recovery", [sys.executable, "recovery_manager.py"], 60),
    ("scaling_plan", [sys.executable, "scaling_manager.py", "--batch-size", "500"], 60),
    ("distributed_manifest", [sys.executable, "distributed_farm.py", "--batch-size", "500"], 60),
]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path):
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"cycle": 0, "stages": {}, "last_success": None, "last_failure": None}


def save_state(state):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.replace(tmp, STATE)


def audit(event):
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def run_stage(name, cmd, timeout_s):
    started = time.time()
    audit({"event": "stage_started", "stage": name, "at": now(), "command": cmd, "timeout_s": timeout_s})
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout_s)
        elapsed = round(time.time() - started, 3)
        result = {"status": "ok" if p.returncode == 0 else "failed", "exit_code": p.returncode, "elapsed_s": elapsed,
                  "stdout_tail": p.stdout[-4000:], "stderr_tail": p.stderr[-4000:]}
    except subprocess.TimeoutExpired as e:
        elapsed = round(time.time() - started, 3)
        result = {"status": "timeout", "exit_code": None, "elapsed_s": elapsed,
                  "stdout_tail": (e.stdout or "")[-4000:] if isinstance(e.stdout, str) else "",
                  "stderr_tail": (e.stderr or "")[-4000:] if isinstance(e.stderr, str) else ""}
    audit({"event": "stage_finished", "stage": name, "at": now(), **result})
    return result


def main():
    state = load_state()
    state["cycle"] = int(state.get("cycle", 0)) + 1
    cycle = state["cycle"]
    state["started_at"] = now()
    save_state(state)
    audit({"event": "cycle_started", "cycle": cycle, "at": state["started_at"]})

    failures = []
    for name, cmd, timeout_s in STAGES:
        result = run_stage(name, cmd, timeout_s)
        state.setdefault("stages", {})[name] = {**result, "cycle": cycle, "at": now()}
        save_state(state)  # checkpoint after every stage
        if result["status"] != "ok":
            failures.append(name)
            # Fail closed for accounting/survival if an upstream stage failed.
            # Later independent analysis stages are not run on corrupted inputs.
            if name in {"discovery", "work_execute", "currency_tests", "verified_payments"}:
                break

    state["finished_at"] = now()
    if failures:
        state["last_failure"] = {"cycle": cycle, "stages": failures, "at": state["finished_at"]}
        audit({"event": "cycle_failed", "cycle": cycle, "at": state["finished_at"], "stages": failures})
        save_state(state)
        print(f"AGENT EVOLUTION CYCLE {cycle}: FAILED stages={failures}")
        return 1

    state["last_success"] = {"cycle": cycle, "at": state["finished_at"]}
    audit({"event": "cycle_completed", "cycle": cycle, "at": state["finished_at"]})
    save_state(state)
    print(f"AGENT EVOLUTION CYCLE {cycle}: COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
