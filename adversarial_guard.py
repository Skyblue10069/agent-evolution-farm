#!/usr/bin/env python3
"""Adversarial integrity checks for agent outputs and payment/work records."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'adversarial_security.json'
BLOCKED=[r'captcha',r'credential theft',r'password dump',r'steal token',r'payment fraud',r'impersonat',r'fake customer',r'fake money',r'anti[- ]?bot bypass',r'phishing']

def scan_text(text):
    low=text.lower(); hits=[p for p in BLOCKED if re.search(p,low)]
    return hits

def run(state=None):
    findings=[]
    if state:
        for a in state.get('agents',[]):
            text=json.dumps({'goals':a.get('brain',{}).get('goals',[]),'plans':a.get('brain',{}).get('plans',[]),'proposals':a.get('proposals',[])})
            hits=scan_text(text)
            if hits: findings.append({'agent_id':a.get('id'),'hits':hits})
    for fname in ('verified_payment_ledger.json','approval_queue.json','agent_proposals.json'):
        p=ROOT/fname
        if p.exists():
            try:
                raw=p.read_text(); hits=scan_text(raw)
                if hits: findings.append({'file':fname,'hits':hits})
            except Exception: pass
    result={'schema_version':1,'status':'quarantined' if findings else 'clean','findings':findings,'rule_count':len(BLOCKED)}
    result['digest']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    OUT.write_text(json.dumps(result,indent=2))
    return result

def main():
    try: state=json.loads((ROOT/'state.json').read_text())
    except Exception: state=None
    r=run(state); print(f'ADVERSARIAL GUARD: {r["status"]} findings={len(r["findings"])}')
    return 1 if r['findings'] else 0
if __name__=='__main__': raise SystemExit(main())
