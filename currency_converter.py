"""Verified-earnings FX conversion/settlement ledger.

A conversion quote is accounting information, not money creation. Only a
provider-confirmed settlement can increase the XAF amount eligible for payout.
"""
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from currency_rate_provider import get_rate

ROOT = Path(__file__).parent
PAYMENTS = ROOT / "verified_payment_ledger.json"
LEDGER = ROOT / "conversion_ledger.json"


def _load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def quote(amount, from_currency, to_currency="XAF"):
    amount = float(amount)
    if amount <= 0:
        raise ValueError("amount must be greater than zero")
    src = str(from_currency).upper().strip()
    dst = str(to_currency).upper().strip()
    rate = get_rate(src, dst)
    return {
        "quote_id": "fxq_" + secrets.token_hex(8),
        "from_currency": src,
        "to_currency": dst,
        "source_amount": round(amount, 2),
        "rate": rate,
        "destination_amount": round(amount * rate, 2),
        "quoted_at": datetime.now(timezone.utc).isoformat(),
        "cash_status": "QUOTE_ONLY"
    }


def record_settlement(source_event_id, from_currency, source_amount, xaf_amount, rate, provider_reference="", agent_id=None):
    """Record a provider-confirmed settlement. This is the only path that
    makes XAF eligible for payout accounting.
    """
    src = str(from_currency).upper().strip()
    amount = float(source_amount)
    xaf = float(xaf_amount)
    if not source_event_id or src == "XAF" or amount <= 0 or xaf <= 0 or rate <= 0:
        raise ValueError("invalid settlement")
    data = _load(LEDGER, {"conversions": []})
    if any(x.get("source_event_id") == source_event_id for x in data["conversions"]):
        return False
    data["conversions"].append({
        "conversion_id": "fx_" + secrets.token_hex(8),
        "source_event_id": source_event_id,
        "from_currency": src,
        "to_currency": "XAF",
        "source_amount": round(amount, 2),
        "xaf_amount": round(xaf, 2),
        "rate": float(rate),
        "provider_reference": provider_reference,
        "agent_id": agent_id,
        "status": "SETTLED_PROVIDER_CONFIRMED",
        "settled_at": datetime.now(timezone.utc).isoformat()
    })
    _save(LEDGER, data)
    return True


def build_settlement_balances():
    """Return actual XAF settlement totals; quotes are deliberately excluded."""
    data = _load(LEDGER, {"conversions": []})
    totals = {}
    for row in data.get("conversions", []):
        if row.get("status") != "SETTLED_PROVIDER_CONFIRMED":
            continue
        totals[row.get("agent_id") or "unassigned"] = round(
            totals.get(row.get("agent_id") or "unassigned", 0) + float(row.get("xaf_amount", 0)), 2
        )
    return totals


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("amount", type=float)
    ap.add_argument("from_currency")
    ap.add_argument("--to", default="XAF")
    a = ap.parse_args()
    print(json.dumps(quote(a.amount, a.from_currency, a.to), indent=2))
