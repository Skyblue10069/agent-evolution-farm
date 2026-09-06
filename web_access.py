"""Persistent web-access gateway for Agent Evolution.
Uses configured provider keys when available and a public-search fallback.
Never bypasses CAPTCHAs, logins, robots controls, or access restrictions.
"""
import html,json,os,re,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).parent
CONFIG=ROOT/'web_access_config.json'
STATE=ROOT/'web_access_state.json'

def _cfg():
    defaults={'providers':['exa','duckduckgo'],'exa_endpoint':'https://api.exa.ai/search','timeout_seconds':8,'max_results':8}
    try: defaults.update(json.loads(CONFIG.read_text()))
    except Exception: pass
    return defaults

def _save_state(event):
    try: state=json.loads(STATE.read_text()) if STATE.exists() else {'requests':0,'provider_stats':{}}
    except Exception: state={'requests':0,'provider_stats':{}}
    state['requests']+=1
    p=event.get('provider','unknown'); stats=state.setdefault('provider_stats',{}).setdefault(p,{'ok':0,'fail':0})
    stats['ok' if event.get('ok') else 'fail']+=1
    state['last_event']=event
    STATE.write_text(json.dumps(state,indent=2))

def _ddg(query,limit,timeout):
    url='https://html.duckduckgo.com/html/?q='+urllib.parse.quote(query)
    req=urllib.request.Request(url,headers={'User-Agent':'AgentEvolution/1.0 (+public-web-research)'})
    with urllib.request.urlopen(req,timeout=timeout) as r: body=r.read().decode('utf-8','ignore')
    out=[]
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',body,re.S):
        href=html.unescape(m.group(1)); title=re.sub('<.*?>','',html.unescape(m.group(2))).strip()
        if href.startswith('//'): href='https:'+href
        if 'uddg=' in href: href=urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('uddg',[href])[0]
        out.append({'title':title,'url':href,'query':query,'provider':'duckduckgo'})
        if len(out)>=limit: break
    return out

def _exa(query,limit,timeout,key,endpoint):
    payload=json.dumps({'query':query,'numResults':limit,'contents':{'text':{'maxCharacters':1200}}}).encode()
    req=urllib.request.Request(endpoint,data=payload,headers={'Content-Type':'application/json','x-api-key':key,'User-Agent':'AgentEvolution/1.0'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as r: data=json.loads(r.read().decode())
    out=[]
    for x in data.get('results',[]):
        out.append({'title':x.get('title',''),'url':x.get('url',''),'query':query,'provider':'exa','text':x.get('text','')})
    return out

def search(query,limit=None):
    cfg=_cfg(); limit=min(int(limit or cfg['max_results']),50); timeout=float(cfg.get('timeout_seconds',8))
    providers=cfg.get('providers',['exa','duckduckgo'])
    key=os.getenv('EXA_API_KEY','').strip()
    for provider in providers:
        try:
            if provider=='exa' and key:
                result=_exa(query,limit,timeout,key,cfg['exa_endpoint'])
            elif provider=='duckduckgo':
                result=_ddg(query,limit,timeout)
            else: continue
            _save_state({'provider':provider,'ok':True,'query':query,'count':len(result)})
            if result: return result
        except Exception as e:
            print(f'web provider failed [{provider}]: {e!r}')
            _save_state({'provider':provider,'ok':False,'query':query,'error':type(e).__name__})
    return []

def fetch(url,max_chars=12000):
    req=urllib.request.Request(url,headers={'User-Agent':'AgentEvolution/1.0 (+public-web-research)'})
    with urllib.request.urlopen(req,timeout=float(_cfg().get('timeout_seconds',8))) as r:
        body=r.read(max_chars*2).decode('utf-8','ignore')
    text=re.sub(r'<script.*?</script>|<style.*?</style>',' ',body,flags=re.S|re.I)
    text=re.sub(r'<[^>]+>',' ',text); text=html.unescape(re.sub(r'\s+',' ',text)).strip()
    return text[:max_chars]
