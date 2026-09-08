"""Execute only already-approved MTN payout proposals."""
import os
from approval_system import execute_mtn, load

def main():
    env = os.getenv("MTN_ENV", "sandbox").lower()
    live = os.getenv("MTN_LIVE_PAYOUT_ENABLED", "false").lower() == "true"
    approved = [
        p for p in load().get("proposals", [])
        if p.get("status") == "APPROVED"
        and p.get("execution_status") not in {"SUBMITTED", "EXECUTED"}
    ]
    if not approved:
        print("PAYOUT EXECUTOR: no approved pending payouts.")
        return 0
    if env == "production" and not live:
        print(f"PAYOUT EXECUTOR: {len(approved)} approved payout(s) held; live execution is disabled.")
        return 0
    failures = 0
    for p in approved:
        try:
            result = execute_mtn(p)
            print(f"PAYOUT EXECUTOR: {p.get('proposal_id')} -> {result.get('execution_status')}")
        except Exception as exc:
            failures += 1
            print(f"PAYOUT EXECUTOR: {p.get('proposal_id')} FAILED: {exc}")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
