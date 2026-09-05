"""Owner-approved Fonlok payout routing.

Only XAF that is already provider-confirmed/settled can enter the Cameroon
payout route. This module never converts money by itself and never bypasses
approval or provider authentication.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
APPROVALS = ROOT / "approval_queue.json"
OUT = ROOT / "payout_routing.json"


def main():
    try:
        ledger = json.loads((ROOT / "verified_payment_ledger.json").read_text()).get("payments", [])
    except Exception:
        ledger = []
    try:
        balances = json.loads((ROOT / "currency_balances.json").read_text())
    except Exception:
        balances = {}
    try:
        approvals = json.loads(APPROVALS.read_text()).get("proposals", [])
    except Exception:
        approvals = []
    approved_ids = {p.get("proposal_id") for p in approvals if p.get("status") == "APPROVED"}
    rows = []
    for p in ledger:
        if not p.get("verified"):
            continue
        rows.append({
            "event_id": p.get("event_id"),
            "agent_id": p.get("agent_id"),
            "provider": p.get("provider"),
            "amount": p.get("amount"),
            "currency": p.get("currency"),
            "xaf_payout_eligible": str(p.get("currency", "")).upper() == "XAF" or p.get("settled_currency") == "XAF",
            "destination_type": "cameroon_mobile_money",
            "receive_only": True,
            "approval_required": True,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        })
    OUT.write_text(json.dumps({
        "provider": "fonlok",
        "environment": os.getenv("FONLOK_ENV", "sandbox"),
        "receive_only_for_incoming": True,
        "destination_type": "cameroon_mobile_money",
        "networks": ["MTN", "ORANGE"],
        "payout_currency": "XAF",
        "balances": balances,
        "payments": rows,
        "approval_required_before_any_use": True,
        "approved_proposals_available": sorted(x for x in approved_ids if x),
        "notes": "Non-XAF earnings must have a provider-confirmed XAF settlement before payout eligibility."
    }, indent=2, ensure_ascii=False))
    print(f"FONLOK ROUTER: {len(rows)} verified payment records mapped; only confirmed XAF is payout-eligible.")


if __name__ == "__main__":
    main()
