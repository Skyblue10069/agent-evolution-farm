"""Stronger economy: double-entry-style event ledger, reserves, cashflow and risk metrics.
All money events must originate from verified provider records or explicit owner actions.
"""
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'economy_engine.json'

def load(p,d):
    try:return json.loads(p.read_text())
    except:return d

def run(state):
    payments=load(ROOT/'verified_payment_ledger.json',{'payments':[]}).get('payments',[])
    db=load(OUT,{'schema':1,'ledger':[],'currency_totals':{},'agent_totals':{},'risk':{},'reserve_policy':{'owner_reserve_required':True,'minimum_reserve_xaf':0}})
    seen={x.get('event_id') for x in db['ledger']}
    for p in payments:
        if not p.get('verified'):continue
        eid=p.get('reference') or hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()
        if eid in seen:continue
        cur=str(p.get('currency','')).upper(); amt=float(p.get('amount',0) or 0)
        if not cur or amt<=0:continue
        db['ledger'].append({'event_id':eid,'type':'VERIFIED_INCOME','agent_id':p.get('agent_id'),'currency':cur,'amount':amt,'timestamp':p.get('verified_at') or datetime.now(timezone.utc).isoformat()}); seen.add(eid)
    totals={}; agents={}
    for e in db['ledger']:
        totals[e['currency']]=round(totals.get(e['currency'],0)+e['amount'],2)
        if e.get('agent_id'):agents.setdefault(e['agent_id'],{}); agents[e['agent_id']][e['currency']]=round(agents[e['agent_id']].get(e['currency'],0)+e['amount'],2)
    db['currency_totals']=totals; db['agent_totals']=agents
    xaf=totals.get('XAF',0); days=max(1,int(state.get('day',1)))
    db['risk']={'verified_xaf':xaf,'average_daily_verified_xaf':round(xaf/days,2),'concentration_top_agent_pct':0,'fake_money_events':0,'unverified_money_events':0}
    if agents and xaf:
        top=max((v.get('XAF',0) for v in agents.values()),default=0); db['risk']['concentration_top_agent_pct']=round(top/xaf*100,2)
    db['ledger']=db['ledger'][-10000:]
    OUT.write_text(json.dumps(db,indent=2,ensure_ascii=False))
