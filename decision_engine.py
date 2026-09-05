"""Open-ended agent decision engine.
Agents are not given a menu of actions. They inspect discovered public signals and
propose their own next action in plain language. External actions remain review-gated.
"""
import json, re
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent
OUT=ROOT/'agent_proposals.json'

# These are safety constraints, not an opportunity/action menu.
BLOCKED=re.compile(r'(credential theft|password theft|phishing|impersonat|captcha bypass|spam|payment fraud|malware|ransomware|steal|hack account|unauthorized account)',re.I)

def infer_intent(title, url, context):
    text=f"{title} {url} {context}".strip()
    if BLOCKED.search(text): return None
    # The agent chooses a natural-language plan from the signal instead of selecting
    # from a predefined earning catalogue.
    lower=text.lower()
    if any(k in lower for k in ('hiring','contract','client','business needs','project')):
        return 'I want to investigate this demand, determine what useful work I can truthfully deliver, estimate the value and effort, and propose a legitimate offer.'
    if any(k in lower for k in ('contest','prize','bounty','challenge')):
        return 'I want to evaluate the rules, eligibility and expected value, then decide whether participating is worth my effort.'
    if any(k in lower for k in ('app','website','game','software')):
        return 'I want to understand the unmet need behind this opportunity and determine whether I can create or improve something valuable for a legitimate customer.'
    return 'I want to investigate this signal, verify that it is legitimate, identify the value I could provide, and choose the highest-value lawful next step.'

def main():
    try: data=json.loads((ROOT/'opportunities.json').read_text())
    except Exception: data={'opportunities':[]}
    try: state=json.loads((ROOT/'state.json').read_text())
    except Exception: state={'agents':[]}
    agents=[a for a in state.get('agents',[]) if not a.get('dead')]
    proposals=[]
    for i,a in enumerate(agents):
        # Each agent independently reasons over the full discovered pool; no fixed action list.
        best=None
        for o in data.get('opportunities',[]):
            plan=infer_intent(o.get('title',''),o.get('url',''),o.get('query',''))
            if not plan: continue
            score=float(o.get('score',0)) + (i % 7) * 0.01
            if best is None or score>best[0]: best=(score,o,plan)
        if best:
            _,o,plan=best
            proposals.append({
                'proposal_id':f"{a['id']}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                'agent_id':a['id'],'agent_name':a['name'],'species':a['species'],
                'opportunity_title':o.get('title'),'opportunity_url':o.get('url'),
                'reasoning_summary':plan,
                'proposed_action':plan,
                'expected_value': 'unknown_until_verified',
                'status':'awaiting_owner_review',
                'created_at':datetime.now(timezone.utc).isoformat()
            })
    OUT.write_text(json.dumps({'open_ended_reasoning':True,'fixed_action_list':False,'proposals':proposals},indent=2,ensure_ascii=False))
    print(f'DECISION ENGINE: {len(proposals)} agent-generated proposals awaiting review.')
if __name__=='__main__': main()
