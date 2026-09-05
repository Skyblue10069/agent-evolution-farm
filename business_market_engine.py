"""Business portfolio engine: capacity, offer lifecycle, experiments and truthful unit economics."""
import json,re,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'business_market_state.json'

def load(p,d):
    try:return json.loads(p.read_text())
    except Exception:return d

def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:48] or 'offer'

def run(state,opps):
    db=load(OUT,{'schema':1,'days':[],'portfolios':{}})
    ranked=sorted(opps,key=lambda x:float(x.get('score',0) or 0),reverse=True)
    for a in state.get('agents',[]):
        if a.get('permanent_status')=='dead': continue
        p=db['portfolios'].setdefault(a['id'],{'owner':a['name'],'offers':{},'capacity':{},'experiments':[],'history':[]})
        completed=int(a.get('completed_work',0)); active=len(a.get('active_work',[])); queued=len(a.get('work_packages',[]))
        p['capacity']={'parallel_limit':2,'active':active,'queued':queued,'available_slots':max(0,2-active)}
        signals=ranked[:12]
        for o in signals:
            title=o.get('title','Demand signal'); key=slug(title)
            offer=p['offers'].setdefault(key,{'name':title,'stage':'hypothesis','observations':0,'completed_deliveries':0,'verified_revenue':{},'experiment_ids':[]})
            offer['observations']+=1
            if completed>0: offer['stage']='testing'
            if offer['verified_revenue']: offer['stage']='validated'
            offer['decision_policy']='retain/expand only after repeated positive evidence; retire after repeated failure or stale demand'
            offer['scope_rule']='scope, price and deadline are set from real customer terms; no invented sales'
        # Generate experiments as hypotheses, never fake results.
        for o in signals[:3]:
            eid=hashlib.sha256(f"{a['id']}:{o.get('title','')}:{len(p['experiments'])}".encode()).hexdigest()[:16]
            if not any(x['id']==eid for x in p['experiments']):
                p['experiments'].append({'id':eid,'offer':slug(o.get('title','')),'hypothesis':'a small truthful offer can validate demand','status':'proposed','result':'unknown'})
        p['experiments']=p['experiments'][-100:]
        p['portfolio_policy']=['test small','measure completion quality','verify payment externally','scale winners','retire weak offers','protect capacity']
        p['history'].append({'day':state.get('day',0),'completed_work':completed,'active_work':active,'offers':len(p['offers'])})
        p['history']=p['history'][-180:]
    db['days'].append({'day':state.get('day',0),'portfolios':len(db['portfolios']),'observed_opportunities':len(opps)})
    db['days']=db['days'][-365:]
    OUT.write_text(json.dumps(db,indent=2,ensure_ascii=False))
