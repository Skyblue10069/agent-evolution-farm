"""Cactus Needle: protected main-character AI layer.
It gets better decision infrastructure, not free money, skills, wins or bypasses.
The 14 MB memory file remains a bounded persistent journal.
"""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent
OUT=ROOT/'cactus_needle_core.json'
MEM=ROOT/'cactus_needle_memory.bin'; CAP=14_000_000

def load(p,d):
    try:return json.loads(p.read_text())
    except Exception:return d

def save(p,o): p.write_text(json.dumps(o,indent=2,ensure_ascii=False))

def run(state):
    cactus=next((a for a in state.get('agents',[]) if a.get('name')=='Cactus Needle'),None)
    if not cactus:return
    db=load(OUT,{'schema':1,'identity':{},'self_tests':[],'mentor_lessons':[],'strategy_map':{},'memory_stats':{}})
    living=[a for a in state.get('agents',[]) if a.get('permanent_status')=='alive' and a.get('id')!=cactus.get('id')]
    # Evidence-weighted mentor lessons: only observable work/reputation/verified revenue fields.
    ranked=sorted(living,key=lambda a:(float(a.get('own_verified_revenue',0) or 0),int(a.get('completed_work',0)),float(a.get('reputation',50))),reverse=True)
    lessons=[]
    for a in ranked[:10]:
        lessons.append({'source_agent':a.get('id'),'lesson':{
            'prefer_completed_work':int(a.get('completed_work',0))>0,
            'reputation':round(float(a.get('reputation',50)),2),
            'verified_revenue_xaf':round(float(a.get('own_verified_revenue',0) or 0),2),
            'rule':'copy decision principles, not claimed outcomes'
        }})
    db['identity']={'name':'Cactus Needle','species':'ai','main_character':True,'protected_identity':True,
                    'memory_capacity_bytes':CAP,'no_free_advantages':True,'same_safety_and_payment_gates':True}
    db['mentor_lessons']=lessons
    # Self-test: check whether the main character is accidentally receiving privileges.
    checks={
      'auto_winner':bool(cactus.get('main_character_is_not_auto_winner') is False),
      'auto_paid':bool(cactus.get('main_character_is_not_auto_paid') is False),
      'skills_from_nothing':sum(float(v or 0) for v in cactus.get('skills',{}).values())>0 and int(cactus.get('completed_work',0))==0,
      'unverified_money':float(cactus.get('own_verified_revenue',0) or 0)<0
    }
    passed=not any(checks.values())
    db['self_tests'].append({'time':datetime.now(timezone.utc).isoformat(),'passed':passed,'violations':checks})
    db['self_tests']=db['self_tests'][-100:]
    db['memory_stats']={'capacity_bytes':CAP,'actual_bytes':MEM.stat().st_size if MEM.exists() else 0,
                        'bounded':(not MEM.exists()) or MEM.stat().st_size<=CAP,
                        'memory_hash':hashlib.sha256(MEM.read_bytes()).hexdigest() if MEM.exists() else None}
    db['operating_mode']={'observe':'enabled','plan':'enabled','critic':'enabled','mentor':'evidence_only','learn':'completed_or_observed_outcomes_only'}
    save(OUT,db)
    print(f'CACTUS NEEDLE: self-test={passed} mentor_lessons={len(lessons)} memory={db["memory_stats"]["actual_bytes"]}/{CAP} bytes')
