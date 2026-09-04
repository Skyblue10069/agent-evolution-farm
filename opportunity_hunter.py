"""Autonomous opportunity discovery.
There is no fixed job/opportunity list. The agent farm generates broad search
queries from its current rules and capabilities, discovers public opportunities,
and filters obvious scams. It never creates fake accounts or bypasses controls.
"""
import argparse,html,json,re,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; OUT=ROOT/"opportunities.json"
RISK=re.compile(r"(pay first|upfront fee|wire transfer|seed phrase|private key|password|gift card|crypto deposit|guaranteed income|account for sale|bank login)",re.I)
PAY=re.compile(r"(?:\$|€|£|USD|EUR|GBP)\s?[0-9][0-9,]*(?:\.[0-9]+)?",re.I)
BASE=[
      # Open-ended earning discovery — these are search seeds, NOT a fixed opportunity list.
      "paid work now","client needs help","business needs service","freelancer wanted","contract work available",
      "remote work opportunity","local business needs help","paid project","commission work","paid competition",
      "paid bounty","sell a service","customers looking for service","ways to earn online legally",
      "ways to earn money with skills","small business needs help","company hiring contractor",
      # Businesses/prospects that publicly signal a need for useful services.
      "business needs website","business needs app","business needs software","business needs automation",
      "business needs video editing","business needs graphic design","business needs marketing",
      "business needs translation","business needs research","business needs social media help",
      "startup needs contractor","shop needs website","restaurant needs website","agency needs contractor",
      "company needs content","company needs data analysis","company needs testing",
      # Legitimate monetization paths to discover and verify, including apps/sites/games.
      "paid user testing","paid usability testing","legitimate research study paid","software testing paid",
      "bug bounty program legal","open source bounty paid","coding challenge prize","game development contest prize",
      "game jam prize","app development contest prize","design contest prize","writing contest prize",
      "creator competition prize","paid survey research study","data labeling paid project",
      "transcription paid project","translation paid project","tutoring paid online","commission marketplace",
      # Worldwide discovery across major regions; results are still independently validated.
      "paid freelance work Africa","paid freelance work Europe","paid freelance work Asia",
      "paid freelance work North America","paid freelance work South America","paid freelance work Middle East",
      "paid freelance work Oceania","business service opportunity Africa","business service opportunity Europe",
      "business service opportunity Asia","business service opportunity North America",
      "business service opportunity South America","business service opportunity Middle East",
      "business service opportunity Oceania"
]

def search(q,limit=8):
    u="https://html.duckduckgo.com/html/?q="+urllib.parse.quote(q)
    req=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=15) as r: body=r.read().decode("utf-8","ignore")
    out=[]
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',body,re.S):
      href=html.unescape(m.group(1)); title=re.sub("<.*?>","",html.unescape(m.group(2))).strip()
      if href.startswith("//"): href="https:"+href
      if "uddg=" in href: href=urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg",[href])[0]
      out.append({"title":title,"url":href,"query":q})
      if len(out)>=limit: break
    return out

def classify(x):
    t=(x.get("title","")+" "+x.get("url","")+" "+x.get("query","")).lower()
    if any(k in t for k in ("business needs","startup needs","shop needs","restaurant needs","agency needs","company needs")): return "business_prospect"
    if any(k in t for k in ("contest","competition","bounty","game jam","challenge prize")): return "prize_or_bounty"
    if any(k in t for k in ("user testing","usability","research study","survey")): return "research_or_testing"
    if any(k in t for k in ("app","website","software","game")): return "digital_opportunity"
    return "paid_work"

def score(x):
    t=(x.get("title","")+" "+x.get("url","")+" "+x.get("query","")).lower()
    if RISK.search(t): return -999
    v=10
    if PAY.search(t): v+=30
    if any(k in t for k in ("paid","pay","hiring","client","contract","project","commission","bounty","prize")): v+=15
    if any(k in t for k in ("urgent","now","today","deadline","apply")): v+=6
    if any(k in t for k in ("business","company","startup","shop","restaurant","agency")): v+=7
    return v

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--max-results",type=int,default=8); ap.add_argument("--max-opportunities",type=int,default=500); args=ap.parse_args()
    queries=list(BASE)
    # Capability discovery is additive, not restrictive: agents can still use any other opportunity.
    try:
      st=json.loads((ROOT/"state.json").read_text())
      skills=list(st.get("agents",[{}])[0].get("skills",{}).keys())
      for k in skills: queries += [f"paid {k}","hiring "+k+" contractor","client needs "+k]
    except Exception: pass
    queries=list(dict.fromkeys(queries)); now=datetime.now(timezone.utc).isoformat(); found=[]
    for q in queries:
      try:
        for x in search(q,args.max_results):
          x["score"]=score(x); x["opportunity_type"]=classify(x); x["discovered_at"]=now; x["worldwide_search"]=True
          if x["score"]>=0: found.append(x)
      except Exception as e: print("search failed",q,e)
    unique={}
    for x in found:
      if x["url"] not in unique or x["score"]>unique[x["url"]]["score"]: unique[x["url"]]=x
    ranked=sorted(unique.values(),key=lambda x:x["score"],reverse=True)[:args.max_opportunities]
    OUT.write_text(json.dumps({"generated_at":now,"autonomous_discovery":True,"fixed_opportunity_list":False,"worldwide_business_search":True,"discovery_policy":"Search publicly available legitimate opportunities, business prospects, apps, websites, games, contests, bounties and other lawful value paths; validate before action.",
      "count":len(ranked),"opportunities":ranked},indent=2,ensure_ascii=False))
    print(f"AUTONOMOUS DISCOVERY: {len(ranked)} opportunities found from {len(queries)} searches.")
if __name__=="__main__": main()
