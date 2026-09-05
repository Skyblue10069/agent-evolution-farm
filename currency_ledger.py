"""Multi-currency verified earnings ledger.

Keeps original payment currencies intact. No exchange-rate conversion is invented.
Only an explicit provider settlement/conversion record may create an XAF value.
"""
import json
from pathlib import Path
ROOT=Path(__file__).parent
LEDGER=ROOT/'verified_payment_ledger.json'
BALANCES=ROOT/'currency_balances.json'

def load_payments():
    try: return json.loads(LEDGER.read_text()).get('payments',[])
    except Exception: return []

def build():
    by_currency={}
    by_agent={}
    settled_xaf={}
    for p in load_payments():
        if not p.get('verified'): continue
        cur=str(p.get('currency','')).upper()
        amt=float(p.get('amount',0) or 0)
        if not cur or amt<=0: continue
        by_currency[cur]=round(by_currency.get(cur,0)+amt,2)
        aid=p.get('agent_id')
        if aid:
            by_agent.setdefault(aid,{})
            by_agent[aid][cur]=round(by_agent[aid].get(cur,0)+amt,2)
        # Only explicit provider-reported settlement/conversion counts as XAF.
        if p.get('settled_currency')=='XAF' and p.get('settled_amount') is not None:
            settled_xaf[aid or 'unassigned']=round(settled_xaf.get(aid or 'unassigned',0)+float(p['settled_amount']),2)
    out={'by_currency':by_currency,'by_agent':by_agent,'settled_xaf_by_agent':settled_xaf}
    BALANCES.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    return out

if __name__=='__main__':
    print(json.dumps(build(),indent=2,ensure_ascii=False))
