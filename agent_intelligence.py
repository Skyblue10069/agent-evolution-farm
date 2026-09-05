"""Advanced intelligence layer: multi-step planning, uncertainty, memory retrieval and decision feedback."""
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent
OUT=ROOT/'intelligence_state.json'

def load(p,d):
    try:return json.loads(p.read_text())
    except:return d

def score(a,o):
    text=(str(o.get('title',''))+' '+str(o.get('description',''))).lower()
    skills=a.get('skills',{})
    fit=sum(v for k,v in skills.items() if k.replace('_',' ') in text or k in text)/max(1,len(skills))
    evidence=float(o.get('evidence_score',0) or 0); reliability=float(o.get('reliability',50) or 50)
    effort=max(1,float(o.get('effort',5) or 5)); risk=float(o.get('risk',0) or 0)
    base=float(o.get('score',0) or 0)
    confidence=max(0,min(100,35+evidence*.35+reliability*.35+fit*3-effort*2-risk*3))
    expected=base*(confidence/100)*max(.1,1-effort*.04)
    return round(expected,3),round(confidence,2)

def run(state, opps, day):
    db=load(OUT,{'schema':1,'days':[],'agent_profiles':{}})
    dayrow={'day':day,'agents':[]}
    for a in state.get('agents',[]):
        if a.get('permanent_status')=='dead': continue
        scored=sorted([(score(a,o),o) for o in opps], key=lambda x:x[0][0], reverse=True)
        top=[]
        for (ev,conf),o in scored[:5]:
            top.append({'title':o.get('title',''),'url':o.get('url',''),'expected_value':ev,'confidence':conf,'next_step':'verify eligibility and requirements'})
        profile=db['agent_profiles'].setdefault(a['id'],{'decisions':0,'wins':0,'replans':0})
        profile['decisions']+=1
        a.setdefault('brain',{})['decision_stack']={'day':day,'options':top,'chosen':top[0] if top else None,'uncertainty':round(100-(top[0]['confidence'] if top else 0),2)}
        a['brain']['counterfactuals']=[{'if':'requirements fail','then':'switch to next ranked opportunity'},{'if':'work blocks externally','then':'persist BLOCKED_EXTERNAL and retry next cycle'}]
        a['brain']['memory_retrieval']=a['brain'].get('lessons',[])[-5:]
        dayrow['agents'].append({'id':a['id'],'chosen':top[0] if top else None})
    db['days'].append(dayrow); db['days']=db['days'][-365:]
    OUT.write_text(json.dumps(db,indent=2,ensure_ascii=False))
