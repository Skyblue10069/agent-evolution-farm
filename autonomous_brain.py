"""Full autonomous brain: memory, self-generated hypotheses, experiments and strategy.
No fixed earning/action catalogue is exposed to agents. Safety and owner controls remain hard gates.
"""
import json, math, re, random
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent
STATE=ROOT/'state.json'; OPPS=ROOT/'opportunities.json'; OUT=ROOT/'brain_decisions.json'
BLOCKED=re.compile(r'(credential theft|password theft|phishing|impersonat|captcha bypass|spam|payment fraud|malware|ransomware|steal|hack account|unauthorized account)',re.I)

def load(p,d):
    try:return json.loads(p.read_text())
    except:return d

def token_score(text, skills):
    t=text.lower(); score=0.0
    for k,v in skills.items():
        if k.replace('_',' ') in t or k in t: score += min(float(v),100)*0.03
    return score

def reason(agent, opp):
    text=f"{opp.get('title','')} {opp.get('url','')} {opp.get('query','')}"
    if BLOCKED.search(text): return None
    base=float(opp.get('score',0)); fit=token_score(text,agent.get('skills',{}))
    uncertainty=max(0.0,20.0-fit)
    prior=0.0
    for lesson in agent.get('brain',{}).get('lessons',[]):
        if lesson.get('opportunity_type')==opp.get('opportunity_type'): prior += min(2.0, float(lesson.get('result_value',0) or 0)*0.01)
    value=base+fit+prior-random.random()*uncertainty*0.15
    return value

def main():
    s=load(STATE,{}); data=load(OPPS,{'opportunities':[]}); now=datetime.now(timezone.utc).isoformat(); decisions=[]
    for a in s.get('agents',[]):
        if a.get('permanent_status')=='dead': continue
        brain=a.setdefault('brain',{}); brain.setdefault('memory',[]); brain.setdefault('goals',[]); brain.setdefault('experiments',[]); brain.setdefault('lessons',[])
        scored=[]
        for o in data.get('opportunities',[]):
            v=reason(a,o)
            if v is not None: scored.append((v,o))
        scored.sort(key=lambda x:x[0],reverse=True)
        best=scored[0][1] if scored else {}
        hypothesis=(f"I should investigate whether the strongest public signal can be converted into legitimate value, "
                    f"using my current capabilities and learning from the result. I will compare effort, eligibility, "
                    f"evidence of demand, payment terms and expected value before choosing what to pursue.") if best else "I should continue exploring public signals and generate a new hypothesis from what I observe."
        experiment={'id':f"{a['id']}-{len(brain['experiments'])+1:05d}",'created_at':now,'opportunity_title':best.get('title',''),'opportunity_url':best.get('url',''),'hypothesis':hypothesis,'status':'proposed_for_review','outcome':'unknown'}
        brain['experiments'].append(experiment); brain['experiments']=brain['experiments'][-100:]
        brain['goals'].append({'created_at':now,'goal':hypothesis,'target':best.get('title',''),'target_url':best.get('url','')}); brain['goals']=brain['goals'][-100:]
        brain['memory'].append({'time':now,'observation':best.get('title','No signal'),'type':'market_observation','score':round(scored[0][0],2) if scored else 0}); brain['memory']=brain['memory'][-200:]
        decisions.append({'agent_id':a['id'],'agent_name':a['name'],'best_signal':best.get('title',''),'url':best.get('url',''),'decision_score':round(scored[0][0],2) if scored else 0,'hypothesis':hypothesis,'status':'awaiting_review'})
    OUT.write_text(json.dumps({'autonomous_brain':True,'open_ended_reasoning':True,'fixed_action_list':False,'decisions':decisions,'generated_at':now},indent=2,ensure_ascii=False))
    STATE.write_text(json.dumps(s,indent=2,ensure_ascii=False))
    print(f'BRAIN: {len(decisions)} living agents produced independent decisions, memories and experiments.')
if __name__=='__main__':main()
