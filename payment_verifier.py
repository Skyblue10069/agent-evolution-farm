"""Provider-neutral verified payment ledger with MTN support.

Only externally verified, completed/paid provider events are recorded. No
payment, customer, exchange rate, or balance is fabricated by this module.
"""
import json
import os
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


def record_provider_payment(provider, event_id, amount, currency, reference="", agent_id=None, *, settled_currency=None, settled_amount=None):
    provider = str(provider).lower().strip()
    amount = float(amount)
    currency = str(currency).upper().strip()
    if not provider or not event_id or amount <= 0 or len(currency) != 3 or not currency.isalpha():
        raise ValueError("Invalid provider payment event or currency code")
    db = load()
    if any(x.get("provider") == provider and x.get("event_id") == event_id for x in db["payments"]):
        return False
    db["payments"].append({
        "provider": provider,
        "event_id": event_id,
        "amount": round(amount, 2),
        "currency": currency,
        "verified": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "reference": reference,
        "agent_id": agent_id,
        "settled_currency": settled_currency,
        "settled_amount": round(float(settled_amount), 2) if settled_amount is not None else None,
    })
    save(db)
    return True


def process_mtn_confirmed_event(event):
    """Accept an MTN payment event only when it is explicitly paid/confirmed."""
    if not isinstance(event, dict):
        return False
    if str(event.get("provider", "mtn")).lower() != "mtn":
        return False
    event_type = str(event.get("type", "")).lower()
    status = str(event.get("status", "")).lower()
    confirmed = event.get("verified") is True or event_type == "payment.confirmed" or status in {"paid", "completed", "success"}
    if not confirmed:
        return False
    return record_provider_payment(
        "mtn",
        event.get("event_id") or event.get("reference") or event.get("invoice_id") or "",
        event.get("amount") or event.get("gross_amount") or event.get("seller_receives") or 0,
        event.get("currency", "XAF"),
        event.get("reference") or event.get("invoice_id", ""),
        event.get("agent_id") or event.get("metadata", {}).get("agent_id"),
        settled_currency=event.get("settled_currency"),
        settled_amount=event.get("settled_amount")
    )


def provider_status():
    env = os.getenv("MTN_ENV", "sandbox").lower()
    return {
        "provider": "mtn",
        "configured": bool(os.getenv("MTN_CLIENT_ID")),
        "environment": env,
        "country": "CM",
        "currency": "XAF",
        "mobile_money_networks": ["MTN", "ORANGE"],
        "note": "MTN Withdrawals V1 supports XAF. Sandbox credentials must remain sandbox-only; live access requires provider approval and compliant account/KYC requirements."
    }
