"""Business scaffolding that grows from discovered businesses/prospects.
The farm searches for real businesses first; a business object is only a strategy
owned by an agent. It is never treated as a fake customer or a fake sale.
"""
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/"businesses"; OUT.mkdir(exist_ok=True)
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")[:50] or "business"
def load(p,d):
    try:return json.loads(p.read_text())
    except Exception:return d

def make_or_update(agent,opps,old=None):
    old=old or {}
    ranked=[x for x in opps if x.get("opportunity_type")=="business_prospect"] or opps
    ranked=sorted(ranked,key=lambda x:float(x.get("score",0)),reverse=True)[:20]
    top=ranked[0] if ranked else {}
    return {**old,
      "owner_agent_id":agent["id"],"owner_name":agent["name"],"species":agent["species"],
      "business_name":old.get("business_name",f"{agent['name']} Works"),
      "status":old.get("status","scaffold"),
      "market_signals":[{"title":x.get("title",""),"url":x.get("url",""),"score":x.get("score",0),"type":x.get("opportunity_type","paid_work")} for x in ranked],
      "current_target":top.get("title","No current public demand signal"),
      "current_target_url":top.get("url",""),
      "services":old.get("services",["Custom service based on confirmed customer demand","Small starter package","Expanded package"]),
      "offer_process":["Find a real public business/customer need","Check eligibility and legitimacy","Define scope","Prepare truthful sample","Agree price/deadline","Deliver through approved channel","Request payment through approved channel","Measure verified result","Adapt offer"],
      "pricing_rule":"Never invent a customer or sale; price only after scope and market terms are confirmed.",
      "created_at":old.get("created_at",datetime.now(timezone.utc).isoformat()),
      "updated_at":datetime.now(timezone.utc).isoformat()}

def main():
    state=load(ROOT/"state.json",{}); opps=load(ROOT/"opportunities.json",{}).get("opportunities",[]); n=0
    for a in state.get("agents",[]):
      path=OUT/f"{slug(a['id'])}.json"; old=load(path,{})
      path.write_text(json.dumps(make_or_update(a,opps,old),indent=2,ensure_ascii=False)); n+=1
    print(f"BUSINESS STRATEGY: {n} agent business strategies updated from real discovered business signals.")
    return n
if __name__=="__main__":main()
