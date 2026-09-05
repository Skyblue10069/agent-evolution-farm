"""Permanent survival mechanics for the Agent Evolution farm.

Deaths are irreversible in the persistent state: a dead agent is moved to the
cemetery and is never respawned or cloned. Survival pressure is based on real
work pipeline progress, not fake cash. Verified external payments can improve
survival resources; discovery alone cannot.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).parent
STATE=ROOT/'state.json'
CEMETERY=ROOT/'cemetery.json'
DAILY=ROOT/'daily_survival.json'

# Pressure is a game mechanic, not a claim of real financial loss.
DAILY_LIFE_COST=1
DEATH_THRESHOLD=0


def now(): return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try: return json.loads(path.read_text()) if path.exists() else default
    except Exception: return default

def save_json(path, obj): path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))

def apply_survival(state, opportunities=0, prepared=0, verified_today=0.0):
    cemetery=load_json(CEMETERY, {"dead_agents":[]})
    cemetery.setdefault('dead_agents', [])
    alive=[]
    deaths=[]
    # Work progress can protect an agent; mere opportunity discovery cannot create money.
    for a in state.get('agents', []):
        a.setdefault('survival', 3)
        a.setdefault('survival_days', 0)
        a.setdefault('last_survival_update', None)
        a.setdefault('permanent_status', 'alive')
        if a.get('permanent_status') == 'dead':
            continue
        a['survival_days'] += 1
        a['survival'] -= DAILY_LIFE_COST
        if prepared > 0:
            a['survival'] += 1
        if verified_today > 0:
            a['survival'] += 2
        if a['survival'] <= DEATH_THRESHOLD:
            a['permanent_status']='dead'
            a['death_day']=state.get('day',0)
            a['death_reason']='survival_resource_reached_zero'
            a['died_at']=now()
            deaths.append(a)
            cemetery['dead_agents'].append({
                'name':a['name'], 'generation':a.get('generation',0),
                'death_day':a['death_day'], 'died_at':a['died_at'],
                'reason':a['death_reason'], 'final_survival':a['survival']
            })
        else:
            a['last_survival_update']=now(); alive.append(a)
    state['agents']=alive
    state['dead_count']=len(cemetery['dead_agents'])
    state['alive_count']=len(alive)
    save_json(CEMETERY,cemetery)
    save_json(DAILY,{
        'timestamp':now(),'alive_agents':len(alive),'dead_agents':len(cemetery['dead_agents']),
        'opportunities_found':opportunities,'packages_prepared':prepared,
        'verified_money_today':round(float(verified_today),2),
        'rule':'Dead agents are permanent and are never respawned.'
    })
    return state, deaths
