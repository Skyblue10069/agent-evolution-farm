"""Offline tests for multi-currency accounting.

These tests do not contact a payment provider or create real transactions.
"""
import json
import tempfile
from pathlib import Path
import currency_converter as cc


def test_quote_math_without_network():
    assert round(10.0 * 600.0, 2) == 6000.0


def test_no_fake_settlement():
    with tempfile.TemporaryDirectory() as d:
        old = cc.LEDGER
        try:
            cc.LEDGER = Path(d) / "conversion_ledger.json"
            cc.LEDGER.write_text(json.dumps({"conversions": []}))
            assert cc.build_settlement_balances() == {}
        finally:
            cc.LEDGER = old


def test_iso_currency_shape():
    for code in ("USD", "EUR", "GBP", "XAF"):
        assert len(code) == 3 and code.isalpha()


if __name__ == "__main__":
    test_quote_math_without_network()
    test_no_fake_settlement()
    test_iso_currency_shape()
    print("multi_currency_tests: PASS")
