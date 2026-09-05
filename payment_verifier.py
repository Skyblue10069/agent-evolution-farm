"""Strict Flutterwave payment verification adapter for Cameroon mobile money.

Only provider-confirmed completed incoming payments become verified money.
This module never fabricates payments and never performs withdrawals/debits.
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
LEDGER = ROOT / "verified_payment_ledger.json"

def load():
    try:
        return json.loads(LEDGER.read_text())
    except Exception:
        return {"payments": []}

def save(data):
    LEDGER.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def record_provider_payment(provider, event_id, amount, currency, reference="", agent_id=None):
    if provider != "flutterwave":
        raise ValueError("Only Flutterwave is enabled as the payment provider")
    amount = float(amount)
    currency = str(currency).upper().strip()
    if not event_id or amount <= 0 or len(currency) != 3 or not currency.isalpha():
        raise ValueError("Invalid provider payment event or currency code")
    db = load()
    if any(x.get("provider") == provider and x.get("event_id") == event_id for x in db["payments"]):
        return False
    db["payments"].append({
        "provider": provider, "event_id": event_id, "amount": round(amount, 2),
        "currency": currency, "verified": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "reference": reference, "agent_id": agent_id,
        "settled_currency": None, "settled_amount": None,
    })
    save(db)
    return True

def process_flutterwave_confirmed_event(event):
    """Accept only an externally verified, completed incoming Flutterwave event."""
    if not isinstance(event, dict):
        return False
    if event.get("provider") != "flutterwave":
        return False
    if event.get("verified") is not True or event.get("completed") is not True:
        return False
    agent_id = event.get("agent_id") or event.get("metadata", {}).get("agent_id")
    return record_provider_payment(
        "flutterwave", event.get("event_id", ""), event.get("amount", 0),
        event.get("currency", ""), event.get("reference", ""), agent_id
    )

def provider_status():
    return {
        "provider": "flutterwave",
        "configured": bool(os.getenv("FLW_SECRET_KEY")),
        "mobile_money_networks": ["MTN", "ORANGE"],
        "country": "CM",
        "currency": "XAF",
        "note": "Flutterwave supports Cameroon mobile money. Live API access requires an approved account and KYC; this project never assumes approval."
    }
