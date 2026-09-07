"""Internal agent marketplace: offers and hires are state records, not fake external sales."""

def run(s):
    market=s.setdefault("agent_marketplace",{"offers":[],"contracts":[]})
    alive=[a for a in s.get("agents",[]) if a.get("permanent_status")=="alive"]
    offers=[]
    for a in alive[:1000]:
        skill=max(a.get("skills",{}),key=a.get("skills",{}).get,default="analysis")
        level=float(a.get("skills",{}).get(skill,0))
        offers.append({"agent_id":a["id"],"skill":skill,"level":round(level,2),"capacity":max(0,100-int(a.get("active_work",0) or 0))})
    market["offers"]=offers
    # Only create internal work contracts backed by existing queued work.
    market["contracts"]=market.get("contracts",[])[-500:]
