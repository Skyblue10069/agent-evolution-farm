"""High-level agent cognition: portfolio decisions, regret tracking, calibration and adaptive strategy selection.
This is decision infrastructure, not a claim of human-like consciousness. It never fabricates outcomes.
"""
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'superintelligence_state.json'

def load(p,d):
    try:return json.loads(p.read_text())
    except Exception:return d

def clamp(x,a=0,b=100): return max(a,min(b,x))

def score(a,o):
    base=float(o.get('score',0) or 0); ev=float(o.get('evidence_score',0) or 0); rel=float(o.get('reliability',50) or 50)
    effort=max(1,float(o.get('effort',5) or 5)); risk=float(o.get('risk',0) or 0)
    skills=a.get('skills',{}); title=(str(o.get('title',''))+' '+str(o.get('description',''))).lower()
    fit=sum(min(100,float(v or 0)) for k,v in skills.items() if k.replace('_',' ') in title or k in title)
    fit=fit/max(1,len(skills))
    completion=clamp(45+fit*.7+rel*.35+ev*.2-effort*4-risk*4)
    # Expected value is deliberately a ranking signal, never a promised income.
    return round(base*(completion/100)*(1-risk/100)*max(.2,1-effort*.03),3), round(completion,2)

def run(state, opps, day):
    db=load(OUT,{'schema':1,'days':[],'agents':{}})
    row={'day':day,'agents':[]}
    for a in state.get('agents',[]):
        if a.get('permanent_status')=='dead': continue
        brain=a.setdefault('brain',{}); profile=db['agents'].setdefault(a['id'],{'attempts':0,'calibration_error':0,'regret':0,'strategies':{}})
        ranked=sorted(((score(a,o),o) for o in opps),key=lambda x:x[0][0],reverse=True)
        shortlist=[]
        for (ev,conf),o in ranked[:8]:
            shortlist.append({'title':o.get('title',''),'url':o.get('url',''),'expected_value_signal':ev,'completion_confidence':conf})
        if shortlist:
            chosen=shortlist[0]
            key=hashlib.sha256(chosen['title'].encode()).hexdigest()[:10]
            strat=profile['strategies'].setdefault(key,{'trials':0,'completed':0,'blocked':0})
            strat['trials']+=1
            action={
                'objective':'maximize legitimate verified value while preserving survival',
                'primary':chosen,
                'fallbacks':shortlist[1:4],
                'preflight':['eligibility','scope','deliverable','external dependency','payment path'],
                'stop_conditions':['unsafe/unauthorized','requirements cannot be met','external dependency blocks execution'],
                'learning_rule':'update strategy only from observed completed/blocked outcomes'
            }
        else:
            action={'objective':'discover and validate a new legitimate opportunity','primary':None,'fallbacks':[],
                    'preflight':['source quality','eligibility','scope'],'stop_conditions':['unsafe/unauthorized'],
                    'learning_rule':'record evidence before changing strategy'}
        brain['superintelligence']=action
        brain['calibration']={'confidence_is_not_success':True,'success_requires_completion_and_evidence':True}
        profile['attempts']+=1
        row['agents'].append({'id':a['id'],'chosen':action['primary']})
    db['days'].append(row); db['days']=db['days'][-365:]
    OUT.write_text(json.dumps(db,indent=2,ensure_ascii=False))
