"""Competitive preparation for publicly discovered opportunities.
Every living agent evaluates every discovered opportunity. The highest-fit agent
gets the draft package; external submission remains review-gated.
"""
import argparse,json,re,html
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; OPPS=ROOT/"opportunities.json"; OUT=ROOT/"work_packages"; OUT.mkdir(exist_ok=True)
def clean(s): return re.sub(r"\s+"," ",html.unescape(s or "")).strip()
def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-")[:70] or "opportunity"
def infer(item):
 t=clean(item.get("title","")+" "+item.get("url","")).lower()
 keys=["coding","writing","video_editing","design","marketing","research","teaching","communication","sales","analysis","languages","data","testing","software","website","app","game"]
 return [k for k in keys if k.replace("_"," ") in t or k in t] or ["research","communication"]
def fit(agent,item):
 text=(item.get("title","")+" "+item.get("url","")).lower(); score=float(item.get("score",0))
 # Skill fit + accumulated learning + business/reputation evidence; every living agent competes.
 for k,v in agent.get("skills",{}).items():
  if k.replace("_"," ") in text or k in text: score += float(v)*2
 brain=agent.get("brain",{})
 score += min(10, len(brain.get("lessons",[]))*0.02)
 score += min(5, len(brain.get("experiments",[]))*0.01)
 return score

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=100); args=ap.parse_args()
 try: data=json.loads(OPPS.read_text()); state=json.loads((ROOT/"state.json").read_text())
 except Exception as e: print("Preparation skipped:",e); return 0
 agents=[a for a in state.get("agents",[]) if a.get("permanent_status")!="dead"]; opps=data.get("opportunities",[])[:args.limit]
 if not agents: print("No living agents."); return 0
 manifest=[]
 for i,item in enumerate(opps,1):
  ranked=sorted(((fit(a,item),a) for a in agents),key=lambda x:x[0],reverse=True); win_score,a=ranked[0]
  title=clean(item.get("title","Public opportunity"))[:180]; skills=infer(item); url=item.get("url","")
  pkg={"agent_id":a["id"],"agent_name":a["name"],"species":a.get("species","animal"),"competition_score":round(win_score,2),"competitors_considered":len(ranked),"opportunity_type":item.get("opportunity_type","paid_work"),"rank":i,"title":title,"url":url,"skills":skills,"created_at":datetime.now(timezone.utc).isoformat(),"status":"prepared_for_review","proposal":f"Hello. I found your public listing for {title}. I can help with {', '.join(skills)}. Before accepting, I would confirm the exact scope, eligibility, deadline, acceptance criteria and payment terms. I can provide an honest sample or portfolio where appropriate.\n\nListing: {url}","workplan":["Confirm requirements and eligibility","Confirm payment terms and deadline","Prepare a small truthful sample when appropriate","Produce the agreed deliverables","Quality-check against acceptance criteria","Deliver through the normal approved channel","Record the real outcome only after it happens"],"deliverable_scaffold":{"requirements":[],"inputs":[],"output_format":"","acceptance_criteria":[],"milestones":[],"qa":[]},"outreach_status":"draft_only","submission_status":"not_submitted","payment_status":"unpaid_unverified"}
  path=OUT/f"{i:04d}-{slug(a['id'])}-{slug(title)}.json"; path.write_text(json.dumps(pkg,indent=2,ensure_ascii=False)); manifest.append({"file":path.name,"agent_id":a["id"],"title":title,"url":url,"opportunity_type":item.get("opportunity_type","paid_work")})
 (OUT/"manifest.json").write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"count":len(manifest),"competition":"all_living_agents_evaluate_each_opportunity","packages":manifest},indent=2,ensure_ascii=False))
 print(f"Prepared {len(manifest)} opportunities after competition across {len(agents)} living agents."); return len(manifest)
if __name__=="__main__": main()
