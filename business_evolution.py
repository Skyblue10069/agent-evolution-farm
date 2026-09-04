"""Autonomous business evolution.
Businesses adapt from discovered demand and verified payment history without inventing customers or sales.
"""
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'businesses'; OUT.mkdir(exist_ok=True)

def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:50] or 'business'

def load_json(path, default):
    try: return json.loads(path.read_text())
    except Exception: return default

def skills_for(text):
    t=(text or '').lower(); skills=['coding','engineering','research','writing','design','marketing','sales','video_editing','project_management','communication','analysis','teaching','languages','crafting','building','farming','cooking','trading']
    return [s for s in skills if s.replace('_',' ') in t][:5]

def evolve(agent, old, opps, payments):
    own=[p for p in payments if p.get('verified') and p.get('agent_id')==agent['id']]
    revenue=round(sum(float(p.get('amount',0)) for p in own),2)
    ranked=sorted(opps,key=lambda x:float(x.get('score',0)),reverse=True)
    signals=ranked[:10]
    text=' '.join(str(x.get('title','')) for x in signals)
    demand_skills=skills_for(text)
    existing=old.get('services',[])
    new_services=list(existing)
    existing_packages=old.get('packages',[])
    new_packages=list(existing_packages)
    for sk in demand_skills:
        label=sk.replace('_',' ').title()
        item=f'{label} service package'
        if item not in new_services: new_services.append(item)
        package=f'{label} — test offer'
        if package not in new_packages: new_packages.append(package)
    if not new_services: new_services=['Customer-demand service package']
    if not new_packages: new_packages=['Demand-led test offer']
    stage='scaffold'
    if revenue>0: stage='validated'
    elif len(agent.get('work_packages',[]))>=3: stage='testing'
    elif demand_skills: stage='market-testing'
    cycle=old.get('evolution_cycle',0)+1
    history=old.get('evolution_history',[])
    history.append({'cycle':cycle,'timestamp':datetime.now(timezone.utc).isoformat(),'revenue_verified':revenue,'demand_skills':demand_skills,'stage':stage})
    return {
      **old,
      'status':stage,
      'evolution_cycle':cycle,
      'market_signals':[{'title':x.get('title',''),'url':x.get('url',''),'score':x.get('score',0)} for x in signals[:10]],
      'services':new_services[:30],
      'packages':new_packages[:30],
      'scaling_policy':'Automatically test, retain, expand or retire offers from observed demand, completed work, experiments and verified revenue; never invent customers or sales.',
      'offer_process':['Detect demand','Define scope','Prepare truthful sample','Test offer','Deliver if accepted','Request payment through approved channel','Measure verified result','Iterate offer'],
      'growth_strategy': 'Expand only from observed demand, completed work, and verified payments; never invent sales.',
      'verified_revenue':revenue,
      'evolution_history':history[-30:],
      'updated_at':datetime.now(timezone.utc).isoformat()
    }

def main():
    state=load_json(ROOT/'state.json',{})
    opps=load_json(ROOT/'opportunities.json',{}).get('opportunities',[])
    payments=load_json(ROOT/'verified_payment_ledger.json',{}).get('payments',[])
    changed=0
    for agent in state.get('agents',[]):
        path=OUT/f'{slug(agent["id"])}.json'
        old=load_json(path,{})
        if not old: continue
        new=evolve(agent,old,opps,payments)
        path.write_text(json.dumps(new,indent=2,ensure_ascii=False)); changed+=1
    print(f'BUSINESS EVOLUTION: {changed} businesses autonomously adapted.')
    return changed
if __name__=='__main__': main()
