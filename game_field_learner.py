"""Persistent evidence-based learning about game data fields.

This module does not guess that a field definitely controls a game mechanic.
It accumulates evidence from repeated observations of accessible save/config
snapshots and optional screen-state labels supplied by the agent. A hypothesis
is promoted only when the same field/value change repeatedly correlates with a
stable observation change. It never bypasses encryption or anti-cheat.
"""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'game_field_learning.json'
DEFAULT={'observations':[],'field_stats':{},'hypotheses':[]}

def load():
    try:return json.loads(STATE.read_text(encoding='utf-8'))
    except:return dict(DEFAULT)
def save(x):STATE.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')
def flatten(v,p='',out=None):
    out={} if out is None else out
    if isinstance(v,dict):
        for k,x in v.items(): flatten(x,f'{p}.{k}' if p else str(k),out)
    elif isinstance(v,list): out[p]=f'array(len={len(v)})'
    else: out[p]=v
    return out

def observe(before:Any,after:Any,observation_change:str=''):
    s=load(); b=flatten(before); a=flatten(after); changed=[]
    for k in sorted(set(b)|set(a)):
        if b.get(k)!=a.get(k):
            changed.append(k)
            st=s.setdefault('field_stats',{}).setdefault(k,{'changes':0,'observed_changes':{},'examples':[]})
            st['changes']+=1
            if observation_change: st['observed_changes'][observation_change]=st['observed_changes'].get(observation_change,0)+1
            if len(st['examples'])<20: st['examples'].append({'before':b.get(k),'after':a.get(k),'observation':observation_change,'ts':time.time()})
    s['observations']=s.get('observations',[])[-999:]+[{'ts':time.time(),'changed_fields':changed,'observation_change':observation_change}]
    hy=[]
    for field,st in s.get('field_stats',{}).items():
        total=st.get('changes',0); obs=st.get('observed_changes',{})
        if total and obs:
            best,label=max((n,k) for k,n in obs.items())
            confidence=min(.99,.5+.1*min(total,5)+.08*min(best,5))
            hy.append({'field':field,'possible_control':label,'confidence':round(confidence,2),'evidence_count':best,'change_count':total})
    s['hypotheses']=sorted(hy,key=lambda x:(-x['confidence'],-x['evidence_count'],x['field']))
    save(s); return {'changed_fields':changed,'hypotheses':s['hypotheses']}

def record_screen_observation(label:str,fields:dict):
    s=load(); s.setdefault('observations',[]).append({'ts':time.time(),'observation_change':label,'field_snapshot':fields}); s['observations']=s['observations'][-1000:]; save(s)
    return {'ok':True,'label':label}
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--label',default=''); ap.add_argument('--before'); ap.add_argument('--after'); args=ap.parse_args()
    if args.before and args.after: print(json.dumps(observe(json.loads(Path(args.before).read_text()),json.loads(Path(args.after).read_text()),args.label),indent=2))
    else: print(json.dumps(load(),indent=2))
