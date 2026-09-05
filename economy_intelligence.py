"""Economic intelligence: verified cashflow, reserves, concentration, liquidity and currency exposure.
No synthetic revenue, synthetic customers or simulated cash is added to the real-money ledger.
"""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'economy_intelligence.json'

def load(p,d):
    try:return json.loads(p.read_text())
    except Exception:return d

def run(state):
    payments=load(ROOT/'verified_payment_ledger.json',{'payments':[]}).get('payments',[])
    db=load(OUT,{'schema':1,'days':[],'currency_exposure':{},'agent_health':{},'controls':{}})
    verified=[p for p in payments if p.get('verified') and float(p.get('amount',0) or 0)>0]
    currencies={}; agents={}
    for p in verified:
        c=str(p.get('currency','')).upper(); amt=float(p.get('amount',0) or 0)
        currencies[c]=round(currencies.get(c,0)+amt,2)
        aid=p.get('agent_id')
        if aid:
            agents.setdefault(aid,{})[c]=round(agents.setdefault(aid,{}).get(c,0)+amt,2)
    xaf=currencies.get('XAF',0); day=max(1,int(state.get('day',1)))
    top=max((v.get('XAF',0) for v in agents.values()),default=0)
    db['currency_exposure']=currencies
    db['agent_health']={aid:{'verified_by_currency':vals,'xaf_share_pct':round(vals.get('XAF',0)/xaf*100,2) if xaf else 0} for aid,vals in agents.items()}
    db['controls']={
      'verified_cash_only':True,'unverified_receivables_excluded':True,'owner_approval_for_outflow':True,
      'minimum_reserve_xaf':100,'reserve_target_xaf':max(100,round(xaf*.10,2)),
      'liquidity_xaf':round(max(0,xaf-max(100,round(xaf*.10,2))),2),
      'average_daily_verified_xaf':round(xaf/day,2),
      'top_agent_concentration_pct':round(top/xaf*100,2) if xaf else 0,
      'currency_conversion_requires_live_rate':True,'payout_requires_provider_confirmation':True
    }
    db['days'].append({'day':state.get('day',0),'verified_income_count':len(verified),'verified_xaf':xaf,'currencies':currencies})
    db['days']=db['days'][-365:]
    OUT.write_text(json.dumps(db,indent=2,ensure_ascii=False))
