"""Live FX rate adapter.

The module fails closed: if a live rate cannot be obtained, no conversion is
created. Rates are never hard-coded and a quote is never treated as cash.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
CACHE = ROOT / "exchange_rates.json"
CONFIG = ROOT / "currency_config.json"


def _config():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def _cache():
    try:
        return json.loads(CACHE.read_text())
    except Exception:
        return {"quotes": {}, "updated_at": None, "provider": None, "source": None}


def _save(data):
    CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _age_seconds(updated_at):
    if not updated_at:
        return None
    try:
        t = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - t).total_seconds())
    except Exception:
        return None


def get_rates(base="USD", symbols=None, timeout=20, allow_cache=True):
    base = str(base).upper().strip()
    if len(base) != 3 or not base.isalpha():
        raise ValueError("base must be a 3-letter ISO currency code")
    cfg = _config()
    template = os.getenv("FX_RATES_URL_TEMPLATE", cfg.get("rate_url_template", "https://open.er-api.com/v6/latest/{base}"))
    url = template.format(base=base)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgentEvolution/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rates = payload.get("rates") or {}
        if payload.get("result") == "error" or not rates:
            raise RuntimeError(str(payload))
        rates = {str(k).upper(): float(v) for k, v in rates.items() if float(v) > 0}
        now = datetime.now(timezone.utc).isoformat()
        cache = {"quotes": {base: rates}, "updated_at": now, "provider": payload.get("provider") or cfg.get("rate_provider"), "source": url}
        _save(cache)
    except Exception:
        if not allow_cache:
            raise
        cache = _cache()
        age = _age_seconds(cache.get("updated_at"))
        max_age = int(cfg.get("rate_max_age_seconds", 86400))
        if cache.get("quotes", {}).get(base) and age is not None and age <= max_age:
            rates = cache["quotes"][base]
        else:
            raise RuntimeError("No fresh live FX rate is available; conversion refused")
    if symbols:
        wanted = {str(x).upper().strip() for x in symbols}
        return {k: rates[k] for k in wanted if k in rates}
    return rates


def get_rate(from_currency, to_currency, timeout=20):
    src = str(from_currency).upper().strip()
    dst = str(to_currency).upper().strip()
    if src == dst:
        return 1.0
    rates = get_rates(src, symbols=[dst], timeout=timeout)
    if dst not in rates:
        raise RuntimeError(f"Rate provider does not currently return {src}->{dst}")
    return float(rates[dst])


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("from_currency")
    ap.add_argument("to_currency", default="XAF", nargs="?")
    a = ap.parse_args()
    print(json.dumps({"from": a.from_currency.upper(), "to": a.to_currency.upper(), "rate": get_rate(a.from_currency, a.to_currency)}, indent=2))
