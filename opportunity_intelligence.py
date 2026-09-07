#!/usr/bin/env python3
"""Open-ended opportunity intelligence: clustering, novelty and saturation.
Never creates opportunities; it only analyzes discovered records."""
from __future__ import annotations
import json,re,math
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'opportunity_intelligence.json'

def tokens(s): return set(re.findall(r'[a-z0-9]{4,}',s.lower()))
def similarity(a,b):
    A,B=tokens(a),tokens(b)
    return len(A&B)/max(1,len(A|B))

def run(opps):
    clusters=[]; assigned={}
    for i,o in enumerate(opps):
        if i in assigned: continue
        group=[i]; assigned[i]=len(clusters)
        for j,p in enumerate(opps[i+1:],i+1):
            if similarity(o.get('title','')+' '+o.get('description',''),p.get('title','')+' '+p.get('description',''))>=0.34:
                group.append(j); assigned[j]=len(clusters)
        clusters.append(group)
    sector=Counter(); source=Counter()
    for o in opps:
        sector[str(o.get('category') or o.get('sector') or 'unknown')]+=1
        source[str(o.get('source') or 'unknown')]+=1
    enriched=[]
    for idx,o in enumerate(opps):
        cid=assigned.get(idx,0); size=len(clusters[cid]); base=float(o.get('score',0) or 0)
        novelty=1/math.sqrt(size); saturation=min(1.0,size/25.0)
        score=round(base*(0.65+0.35*novelty)*(1-0.25*saturation),4)
        x=dict(o); x['cluster_id']=cid; x['cluster_size']=size; x['novelty']=round(novelty,4); x['saturation']=round(saturation,4); x['intelligence_score']=score; enriched.append(x)
    out={'schema_version':1,'opportunity_count':len(opps),'cluster_count':len(clusters),'sector_counts':dict(sector),'source_counts':dict(source),'opportunities':enriched}
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)); (ROOT/'opportunities.json').write_text(json.dumps({'opportunities':enriched},indent=2,ensure_ascii=False))
    return out

def main():
    try: opps=json.loads((ROOT/'opportunities.json').read_text()).get('opportunities',[])
    except Exception: opps=[]
    r=run(opps); print(f'OPPORTUNITY INTELLIGENCE: opportunities={r["opportunity_count"]} clusters={r["cluster_count"]}')
if __name__=='__main__': main()
