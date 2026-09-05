"""Dynamic trust + activity ledger for Agent Evolution.
Trust changes from observed work quality/results, never from promises alone.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent
HISTORY=ROOT/'agent_activity_history.json'
RULES=ROOT/'rules.json'

def now(): return datetime.now(timezone.utc).isoformat()
def load():
    try: return json.loads(HISTORY.read_text())
    except Exception: return {"agents":{}}
def save(x): HISTORY.write_text(json.dumps(x,indent=2,ensure_ascii=False))
def score_from_metrics(work=0, success=0, revenue=0, failures=0, quality=0):
    return max(-12, min(18, round(work*2 + success*4 + min(10,float(revenue)/10000) + quality*0.08 - failures*4, 2)))
def record_agent(agent, event_type, summary, *, quality=0, successful=False, revenue=0, currency=None, failure=False, work=False):
    data=load(); aid=agent['id']; x=data['agents'].setdefault(aid,{"name":agent.get('name',aid),"trust_score":0.0,"completed_work":0,"successful_runs":0,"verified_revenue":0.0,"failures":0,"funding_requests":0,"approved_requests":0,"rejected_requests":0,"events":[]})
    x['name']=agent.get('name',x['name']); x['completed_work'] += int(work); x['successful_runs'] += int(successful); x['failures'] += int(failure)
    x.setdefault('earnings_by_currency', {})
    x.setdefault('verified_revenue_xaf', 0.0)
    if currency:
        cur=str(currency).upper(); x['earnings_by_currency'][cur]=round(x['earnings_by_currency'].get(cur,0)+float(revenue),2)
        if cur == 'XAF':
            x['verified_revenue_xaf']=round(x.get('verified_revenue_xaf',0)+float(revenue),2)
            x['verified_revenue']=x['verified_revenue_xaf']
    else:
        x['verified_revenue_xaf']=round(x.get('verified_revenue_xaf',0)+float(revenue),2)
        x['verified_revenue']=x['verified_revenue_xaf']
    delta=score_from_metrics(int(work),int(successful),float(revenue),int(failure),float(quality)); x['trust_score']=round(max(0,min(100,x['trust_score']+delta)),2)
    x['events'].append({'timestamp':now(),'type':event_type,'summary':summary,'quality':quality,'trust_delta':delta,'trust_after':x['trust_score']})
    x['events']=x['events'][-100:]; save(data); return x


def record_snapshot(agent, day=None):
    """Store a time-series checkpoint for dashboard graphs."""
    data=load(); aid=agent['id']
    x=data['agents'].setdefault(aid,{"name":agent.get('name',aid),"trust_score":0.0,"completed_work":0,"successful_runs":0,"verified_revenue":0.0,"failures":0,"funding_requests":0,"approved_requests":0,"rejected_requests":0,"events":[],"snapshots":[]})
    x.setdefault('snapshots', [])
    snap={
      'timestamp':now(), 'day':int(day if day is not None else agent.get('days_active',0)),
      'trust':round(float(x.get('trust_score',0)),2),
      'earnings':round(float(x.get('verified_revenue_xaf',x.get('verified_revenue',agent.get('own_verified_revenue',0)))),2),
      'earnings_by_currency':dict(x.get('earnings_by_currency',agent.get('earnings_by_currency',{}))),
      'skills':{k:round(float(v),2) for k,v in agent.get('skills',{}).items()}
    }
    x['snapshots'].append(snap); x['snapshots']=x['snapshots'][-180:]; save(data); return snap

def sync_from_state(state):
    data=load()
    for a in state.get('agents',[]):
        x=data['agents'].setdefault(a['id'],{"name":a.get('name',a['id']),"trust_score":0.0,"completed_work":0,"successful_runs":0,"verified_revenue":0.0,"failures":0,"funding_requests":0,"approved_requests":0,"rejected_requests":0,"events":[]})
        x['name']=a.get('name',x['name'])
    save(data); return data

def can_request(agent_id):
    data=load(); x=data['agents'].get(agent_id,{}); r={}
    try: r=json.loads(RULES.read_text()).get('owner_rules',{})
    except Exception: pass
    threshold=float(r.get('funding_trust_threshold',35)); minimum=int(r.get('minimum_work_before_funding',2))
    return x.get('trust_score',0)>=threshold and x.get('completed_work',0)>=minimum

def snapshot(agent_id): return load().get('agents',{}).get(agent_id,{})
