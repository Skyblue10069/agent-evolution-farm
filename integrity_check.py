#!/usr/bin/env python3
"""Fast preflight checks for GitHub Actions without creating __pycache__ files."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = [
    "simulate.py", "autonomous_brain.py", "evolution_system.py", "agent_intelligence.py",
    "agent_superintelligence.py", "worldwide_discovery.py", "internet_agent.py", "web_access.py",
    "work_preparer.py", "work_executor.py", "business_factory.py", "business_evolution.py",
    "business_ecosystem.py", "economy_engine.py", "economy_intelligence.py", "currency_ledger.py",
    "payment_verifier.py", "payout_router.py", "approval_system.py", "evolution_upgrade.py", "scaling_manager.py", "lineage_replay.py", "adversarial_guard.py", "opportunity_intelligence.py", "evolution_lab_max.py", "distributed_farm.py", "api_adapters.json", "rules.json",
]


def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        print("Missing required files:", missing)
        return 1

    errors = []
    for p in sorted(ROOT.glob("*.py")):
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except Exception as exc:
            errors.append(f"{p.name}: {exc}")
    if errors:
        print("Python syntax failures:")
        print("\n".join(errors))
        return 1

    # Ensure no obvious secret material is committed in JSON config files.
    for p in ROOT.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        raw = json.dumps(data).lower()
        if any(k in raw for k in ["api_key=", "password=", "secret="]):
            print(f"Potential inline secret marker in {p.name}; use GitHub Secrets instead.")
            return 1

    print("Preflight OK: required modules parse and no obvious inline-secret markers found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
