"""Advanced agent-owned business layer: offers, pipelines, unit economics and lifecycle."""
import json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'business_ecosystem.json'

def load(p,d):
    try:return json.loads(p.read_text())
    except:return d

def run(state, opps):
    db=load(OUT,{'schema':1,'businesses':{},'market_tests':[]})
    signals=sorted(opps,key=lambda x:float(x.get('score',0) or 0),reverse=True)
    for a in state.get('agents',[]):
        if a.get('permanent_status')=='dead': continue
        b=db['businesses'].setdefault(a['id'],{'owner':a['name'],'stage':'idea','offers':[],'pipeline':[],'experiments':[],'metrics':{'verified_revenue':0,'completed_work':0}})
        top=signals[:8]
        for o in top:
            title=o.get('title','Demand signal')
            key=re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-')[:45]
            if key and not any(x.get('key')==key for x in b['offers']):
                b['offers'].append({'key':key,'name':title,'status':'hypothesis','evidence_url':o.get('url',''),'pricing':'set only after real scope/terms are confirmed'})
        completed=int(a.get('completed_work',0)); revenue=float(a.get('own_verified_revenue',0) or 0)
        b['metrics']={'verified_revenue':revenue,'completed_work':completed,'reputation':a.get('reputation',50)}
        if revenue>0:b['stage']='validated'
        elif completed>0:b['stage']='testing'
        elif b['offers']:b['stage']='market-testing'
        b['unit_economics']={'revenue':'provider_verified_only','costs':'recorded_only','margin':'computed only from observed values'}
        b['pipeline_rules']=['no invented leads','no invented sales','no fake invoices','qualify -> scope -> deliver -> verify payment -> retain/expand']
    OUT.write_text(json.dumps(db,indent=2,ensure_ascii=False))
