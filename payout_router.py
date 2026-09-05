"""Receive-only Flutterwave mobile-money routing policy.

Verified incoming payments are mapped to the owner's configured MTN/Orange
mobile-money destination. No withdrawal or debit operation is implemented.
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).parent
APPROVALS = ROOT / "approval_queue.json"
OUT = ROOT / "payout_routing.json"

def main():
    try:
        ledger = json.loads((ROOT/"verified_payment_ledger.json").read_text()).get("payments", [])
    except Exception:
        ledger = []
    destination = os.getenv("PAYOUT_DESTINATION_ID", "")
    try:
        approvals = json.loads(APPROVALS.read_text()).get("proposals", [])
    except Exception:
        approvals = []
    approved_ids = {p.get("proposal_id") for p in approvals if p.get("status") == "APPROVED"}
    network = os.getenv("PAYOUT_MOBILE_MONEY_NETWORK", "")
    rows = []
    for p in ledger:
        if p.get("verified") and p.get("provider") == "flutterwave":
            rows.append({
                "event_id": p.get("event_id"), "agent_id": p.get("agent_id"),
                "provider": "flutterwave", "amount": p.get("amount"),
                "currency": p.get("currency"), "destination_configured": bool(destination),
                "destination_id_label": "configured_owner_mobile_money" if destination else "NOT_CONFIGURED",
                "mobile_money_network": network or "NOT_CONFIGURED",
                "receive_only": True, "no_withdrawals": True,
                "approved_proposals": len(approved_ids),
                "recorded_at": datetime.now(timezone.utc).isoformat()
            })
    OUT.write_text(json.dumps({
        "provider":"flutterwave", "receive_only":True, "no_withdrawals":True,
        "destination_type":"cameroon_mobile_money", "payments":rows,
        "approval_required_before_any_use": True,
        "approved_proposals_available": sorted(x for x in approved_ids if x)
    }, indent=2, ensure_ascii=False))
    print(f"FLUTTERWAVE ROUTER: {len(rows)} verified incoming payments mapped to receive-only mobile-money routing records.")
if __name__ == "__main__": main()
