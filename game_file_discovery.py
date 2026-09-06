"""Automatic discovery and structural learning for user-authorized game data.

The scanner only inspects directories already granted in game_file_policy.json.
It classifies files, parses safe text formats, inventories fields, and records
hypotheses about what fields may represent. It never bypasses Android storage,
DRM, anti-cheat, encryption, or authentication.

Optional experiment mode operates only on copies exported to an experiment
workspace; it never silently mutates the original save/config.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, re, shutil, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
POLICY=ROOT/"game_file_policy.json"
STATE=ROOT/"game_file_discovery_state.json"
SCHEMA=ROOT/"game_file_schemas.json"
EXPERIMENTS=ROOT/"game_file_experiments"

DEFAULT={
  "enabled":True,
  "auto_discover":True,
  "max_files":5000,
  "max_depth":8,
  "max_file_mb":32,
  "allowed_extensions":[".json",".json5",".txt",".ini",".cfg",".conf",".xml",".yaml",".yml",".properties",".mcfunction",".mcstructure",".dat",".sav",".save"],
  "experiment_on_copies":False,
  "max_experiment_fields":20
}

def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return copy.deepcopy(d)
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
def sha(b):return hashlib.sha256(b).hexdigest()

def safe_policy():
    p={**DEFAULT,**load(POLICY,DEFAULT)}
    if not p.get('enabled',True): raise PermissionError('game file editing/discovery disabled')
    roots=[Path(x).expanduser().resolve() for x in p.get('allowed_roots',[])]
    if not roots: raise PermissionError('No user-authorized game-data root is configured')
    return p,roots

def under(path,roots): return any(path==r or r in path.parents for r in roots)

def scalar_kind(v):
    if isinstance(v,bool):return 'boolean'
    if isinstance(v,int) and not isinstance(v,bool):return 'integer'
    if isinstance(v,float):return 'number'
    if isinstance(v,str):return 'string'
    if v is None:return 'null'
    if isinstance(v,list):return 'array'
    if isinstance(v,dict):return 'object'
    return type(v).__name__

def semantic_hint(path,value):
    tokens=[t for t in re.split(r'[^a-zA-Z0-9]+',path.lower()) if t]
    hints=[]
    groups={
      'level':{'level','lvl','rank','stage'}, 'experience':{'xp','experience','exp'},
      'health':{'health','hp','hitpoints'}, 'mana':{'mana','mp'},
      'currency':{'money','cash','coins','gold','credits','currency','balance'},
      'damage':{'damage','dmg','attack','atk'}, 'defense':{'defense','defence','armor','armour'},
      'speed':{'speed','velocity'}, 'inventory':{'inventory','items','backpack'},
      'position':{'position','pos','coordinate','coordinates'}, 'seed':{'seed'},
      'unlocks':{'unlock','unlocked','achievement','achievements'}, 'difficulty':{'difficulty'},
      'settings':{'setting','settings','config','option','options','enabled','volume','quality'},
      'timer':{'time','timer','duration','cooldown'}, 'name':{'name','username','player'}
    }
    for meaning,words in groups.items():
        if any(t in words for t in tokens): hints.append(meaning)
    if tokens and tokens[-1] in {'x','y','z'} and ('position' in tokens or any(t in {'pos','coordinate','coordinates'} for t in tokens)):
        hints.append('position')
    if isinstance(value,(int,float)) and abs(value)>10**9: hints.append('large_numeric_or_timestamp')
    return sorted(set(hints))

def walk(v,prefix='',depth=0,out=None):
    out=[] if out is None else out
    if depth>20:return out
    if isinstance(v,dict):
        for k,val in v.items():
            path=f'{prefix}.{k}' if prefix else str(k)
            out.append({'path':path,'type':scalar_kind(val),'sample':val if scalar_kind(val) in ('string','boolean','null') else (val if scalar_kind(val) in ('integer','number') else None),'hints':semantic_hint(path,val)})
            walk(val,path,depth+1,out)
    elif isinstance(v,list):
        for i,val in enumerate(v[:100]): walk(val,f'{prefix}[{i}]',depth+1,out)
    return out

def parse_text(path,data):
    ext=path.suffix.lower()
    if ext in {'.json','.json5'}:
        try:return json.loads(data.decode('utf-8'))
        except Exception:return None
    return None

def scan_file(path,root):
    try:
        data=path.read_bytes()
        rec={'path':str(path),'relative':str(path.relative_to(root)),'size':len(data),'sha256':sha(data),'extension':path.suffix.lower()}
        try:text=data.decode('utf-8')
        except UnicodeDecodeError:text=None
        obj=parse_text(path,data)
        if obj is not None:
            fields=walk(obj)
            rec.update({'format':'json','root_type':scalar_kind(obj),'field_count':len(fields),'fields':fields[:10000]})
        elif text is not None:
            lines=text.splitlines()
            pairs=[]
            for line in lines[:10000]:
                s=line.strip()
                if not s or s.startswith(('#',';','//')):continue
                m=re.match(r'^([^:=]+)\s*[:=]\s*(.*?)\s*$',s)
                if m:
                    key,val=m.group(1).strip(),m.group(2).strip()
                    pairs.append({'path':key,'type':'string','sample':val[:200],'hints':semantic_hint(key,val)})
            rec.update({'format':'text','root_type':'text','field_count':len(pairs),'fields':pairs})
        else:
            rec.update({'format':'binary','root_type':'binary','field_count':0,'fields':[]})
        return rec
    except Exception as e:return {'path':str(path),'relative':str(path.relative_to(root)),'error':str(e)}

def discover():
    p,roots=safe_policy(); state=load(STATE,{'runs':0,'files':{},'hypotheses':[]})
    results=[]; seen=0
    for root in roots:
        if not root.exists() or not root.is_dir():continue
        for path in root.rglob('*'):
            if seen>=int(p['max_files']):break
            if not path.is_file() or path.suffix.lower() not in p['allowed_extensions']:continue
            try:
                if len(path.relative_to(root).parts)>int(p['max_depth']): continue
                if path.stat().st_size>int(p['max_file_mb'])*1024*1024:continue
            except OSError:continue
            results.append(scan_file(path,root)); seen+=1
    for r in results:
        state['files'][r['path']]={'sha256':r.get('sha256'),'size':r.get('size'),'field_count':r.get('field_count',0),'last_seen':time.time()}
    state['runs']=int(state.get('runs',0))+1; state['last_run']=time.time(); state['file_count']=len(results)
    state['hypotheses']=build_hypotheses(results)
    save(STATE,state); save(SCHEMA,{'generated_at':time.time(),'files':results,'hypotheses':state['hypotheses']})
    return {'ok':True,'files':len(results),'hypotheses':len(state['hypotheses']),'schema_file':str(SCHEMA)}

def build_hypotheses(results):
    out=[]
    for r in results:
        for f in r.get('fields',[]):
            if f.get('hints'):
                out.append({'file':r['path'],'field':f['path'],'type':f['type'],'possible_meanings':f['hints'],'confidence':round(min(.98,.55+.08*len(f['hints'])),2),'evidence':'name/type heuristic'})
    return out

def experiment_copy(path):
    p,roots=safe_policy(); src=Path(path).expanduser().resolve()
    if not under(src,roots):raise PermissionError('File is outside authorized roots')
    if not src.is_file():raise FileNotFoundError(path)
    EXPERIMENTS.mkdir(exist_ok=True)
    dest=EXPERIMENTS/(src.name+f'.copy-{int(time.time())}')
    shutil.copy2(src,dest)
    return dest

if __name__=='__main__':
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('discover')
    e=sub.add_parser('experiment-copy'); e.add_argument('path')
    args=ap.parse_args()
    if args.cmd=='discover':out=discover()
    else:out={'ok':True,'copy':str(experiment_copy(args.path))}
    print(json.dumps(out,indent=2))
