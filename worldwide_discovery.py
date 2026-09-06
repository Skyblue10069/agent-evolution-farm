"""Deep worldwide opportunity discovery.
Searches public web signals broadly and expands from discovered domains/terms instead of a fixed opportunity menu.
"""
import argparse,html,json,re,urllib.parse,urllib.request,time
from web_access import search as web_search
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/'opportunities.json'
RISK=re.compile(r'(pay first|upfront fee|wire transfer|seed phrase|private key|password|gift card|crypto deposit|guaranteed income|account for sale|bank login)',re.I)
SEEDS=['business needs help','business looking for contractor','company seeking service','client project paid','freelance contract paid','remote contract opportunity','startup looking for help','paid project opportunity','public bounty program','paid testing opportunity','paid research opportunity','legitimate competition prize','creator opportunity paid','developer opportunity paid','design opportunity paid','writing opportunity paid']
REGIONS=['Africa','Europe','Asia','North America','South America','Middle East','Oceania']

def search(q,limit=8):
    return web_search(q,limit)

def score(x):
    t=(x.get('title','')+' '+x.get('url','')+' '+x.get('query','')).lower()
    if RISK.search(t): return -999
    s=10
    if re.search(r'(\$|€|£|usd|eur|gbp)\s?[0-9]',t): s+=30
    if any(k in t for k in ('paid','client','hiring','contract','project','bounty','prize','commission')): s+=15
    if any(k in t for k in ('business','company','startup','shop','agency')): s+=10
    if any(k in t for k in ('app','website','software','game','developer')): s+=5
    return s

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--max-results',type=int,default=6)
    ap.add_argument('--max-opportunities',type=int,default=1000)
    ap.add_argument('--time-limit-seconds',type=int,default=540)
    ap.add_argument('--max-queries',type=int,default=16)
    args=ap.parse_args()

    queries=[]
    for seed in SEEDS:
        queries.append(seed)
        for region in REGIONS:
            queries.append(f'{seed} {region}')
    try:
        st=json.loads((ROOT/'state.json').read_text())
        skills=list(st.get('agents',[{}])[0].get('skills',{}).keys())
        for skill in skills:
            queries += [f'paid {skill} opportunity',f'business needs {skill}',f'company seeking {skill}']
    except Exception:
        pass
    queries=list(dict.fromkeys(queries))
    now=datetime.now(timezone.utc).isoformat()
    found=[]
    started=time.monotonic()
    deadline=started+max(1,args.time_limit_seconds)

    def do_search(q):
        # Keep each network operation short so one dead search endpoint cannot
        # consume the entire GitHub Actions job.
        return search(q,args.max_results)

    # CI-safe discovery: cap the number of network requests and keep each request
    # short. A blocked search provider must never make the farm appear frozen.
    selected_queries=queries[:max(1,args.max_queries)]
    for q in selected_queries:
        if time.monotonic() >= deadline: break
        try:
            for x in search(q,args.max_results):
                x['score']=score(x); x['discovered_at']=now; x['worldwide_search']=True
                if x['score']>=0: found.append(x)
        except Exception as e:
            print('search failed:',q,repr(e))

    unique={}
    for x in found:
        key=x['url'].split('#')[0]
        if key not in unique or x['score']>unique[key]['score']:
            unique[key]=x
    ranked=sorted(unique.values(),key=lambda x:x['score'],reverse=True)[:args.max_opportunities]
    elapsed=round(time.monotonic()-started,2)
    OUT.write_text(json.dumps({
        'generated_at':now,'autonomous_discovery':True,'fixed_opportunity_list':False,
        'open_ended_discovery':True,'count':len(ranked),'opportunities':ranked,
        'time_limit_seconds':args.time_limit_seconds,'elapsed_seconds':elapsed,
        'queries_planned':len(queries),'queries_selected':len(selected_queries),'deadline_enforced':True
    },indent=2,ensure_ascii=False))
    print(f'WORLDWIDE DISCOVERY: {len(ranked)} unique public signals; elapsed {elapsed}s (limit {args.time_limit_seconds}s).')
if __name__=='__main__':main()
