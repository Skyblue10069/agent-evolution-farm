"""Concurrent task planner for agents.

An agent may voluntarily run several legitimate work items at once. Capacity is
learned from planning/focus/discipline; every task still passes the existing
work-completion gates. This never creates revenue by itself.
"""
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
QUEUE=ROOT/'work_queue.json'


def load():
    try:return json.loads(QUEUE.read_text())
    except:return {"items":[]}

def save(x):QUEUE.write_text(json.dumps(x,indent=2,ensure_ascii=False))


def run(state):
    queue=load(); items=queue.setdefault("items",[])
    opps=[]
    try: opps=json.loads((ROOT/'opportunities.json').read_text()).get('opportunities',[])
    except Exception: pass
    by_url={o.get('url',''):o for o in opps}
    now=datetime.now(timezone.utc).isoformat()
    created=0
    for a in state.get('agents',[]):
        if a.get('permanent_status')!='alive': continue
        capacity=int(a.get('task_capacity',2) or 2)
        capacity=max(1,min(6,capacity))
        active=[x for x in items if x.get('agent_id')==a.get('id') and x.get('status') not in ('COMPLETED','BLOCKED_EXTERNAL')]
        if len(active)>=capacity: continue
        # Prefer the agent's current ranked goals, then discovered opportunities.
        preferred=[]
        for g in reversed(a.get('brain',{}).get('goals',[])):
            u=g.get('url','')
            if u and u in by_url and u not in [x.get('opportunity_url') for x in active]: preferred.append(by_url[u])
        candidates=preferred+[o for o in opps if o.get('url','') not in [x.get('opportunity_url') for x in active]]
        for o in candidates:
            if len(active)>=capacity: break
            url=o.get('url','')
            if not url: continue
            if any(x.get('opportunity_url')==url for x in active): continue
            tid=hashlib.sha256(f"{a['id']}|{url}|{state.get('day',0)}".encode()).hexdigest()[:16]
            task={'id':tid,'agent_id':a['id'],'opportunity_url':url,'title':o.get('title','Opportunity'),
                  'status':'IN_PROGRESS','attempts':0,'started_day':state.get('day',0),
                  'last_updated':now,'completion_required':True,'external_submission_required':False,
                  'payment_status':'unpaid_unverified','multitask_slot':len(active)+1}
            items.append(task); active.append(task); created+=1
        a['active_work']=[x['id'] for x in active]
        a['brain'].setdefault('plans',[]).append({'day':state.get('day',0),'type':'multitask_plan','capacity':capacity,'tasks':[x['id'] for x in active]})
        a['brain']['plans']=a['brain']['plans'][-50:]
    queue['multitask_summary']={'last_run':now,'created':created,'max_capacity':max((int(a.get('task_capacity',1)) for a in state.get('agents',[]) if a.get('permanent_status')=='alive'),default=1)}
    save(queue)
    return created
