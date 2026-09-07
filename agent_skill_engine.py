"""Adaptive skill + meta-learning engine.

All skills start at zero. Experience, completed work, experiments, delegation,
and verified outcomes shape capability over time. No skill is assigned as a job.
"""
import math, random

META_SKILLS = [
    "learning_speed","memory_management","reasoning","planning","research",
    "problem_solving","creativity","decision_making","adaptability","self_criticism",
    "prediction","negotiation","communication","delegation","leadership","teamwork",
    "resource_management","risk_management","opportunity_discovery","business_strategy",
    "customer_understanding","quality_control","automation_design","technical_skill",
    "economic_intelligence","competitive_intelligence","portfolio_management","failure_recovery",
    "meta_learning","self_improvement"
]
TRAITS = ["curiosity","focus","patience","risk_tolerance","creativity","discipline","cooperation","independence"]


def _clamp(x, lo=0.0, hi=100.0):
    return round(max(lo, min(hi, float(x))), 3)


def ensure(a):
    skills=a.setdefault("skills",{})
    for k in META_SKILLS:
        skills.setdefault(k, 0.0)
    traits=a.setdefault("traits",{})
    for t in TRAITS:
        traits.setdefault(t, round(random.Random(f"{a.get('id')}:{t}").random(),3))
    brain=a.setdefault("brain",{})
    brain.setdefault("meta_learning", {"best_methods":[],"skill_gaps":[],"recent_lessons":[]})
    brain.setdefault("skill_history", [])
    brain.setdefault("plans", [])
    return a


def _learn_rate(a):
    s=a.get("skills",{})
    return 0.15 + min(1.5, float(s.get("learning_speed",0))/70.0) + float(a.get("traits",{}).get("curiosity",0.5))*0.4


def learn_from_outcomes(a, day):
    ensure(a)
    s=a["skills"]; brain=a["brain"]
    completed=int(a.get("completed_work",0) or 0); failed=int(a.get("failed_work",0) or 0)
    wins=int(a.get("wins",0) or 0); losses=int(a.get("losses",0) or 0)
    recent=completed+failed+1
    signal=(completed*1.5+wins*0.8-failed*0.5-losses*0.3)/recent
    rate=_learn_rate(a)
    mapping={
      "reasoning":["analysis","strategy"], "planning":["project_management","strategy"],
      "research":["research","analysis"], "problem_solving":["engineering","coding"],
      "communication":["communication","writing","languages"], "negotiation":["diplomacy","sales"],
      "leadership":["leadership","project_management"], "teamwork":["communication","diplomacy"],
      "technical_skill":["coding","engineering"], "business_strategy":["marketing","sales","strategy"],
      "economic_intelligence":["trading","analysis"], "quality_control":["analysis","project_management"],
      "automation_design":["coding","engineering"], "opportunity_discovery":["research","exploration"],
      "adaptability":["strategy","exploration"], "failure_recovery":["strategy","problem_solving"],
      "self_improvement":["analysis","strategy"], "meta_learning":["analysis","teaching"],
    }
    base_gain=max(0.02, rate*(0.18+max(0,signal)*0.08))
    for meta, bases in mapping.items():
        source=sum(float(s.get(x,0) or 0) for x in bases)/len(bases)
        # Meta skills can grow from outcomes even when their source skills are low.
        gain=base_gain*(1.0+source/120.0)
        if completed: gain += min(0.8, completed*0.01)
        if failed: gain -= min(0.35, failed*0.006)
        s[meta]=_clamp(s.get(meta,0)+gain)
    # Fill the remaining meta skills with a slower general learning signal.
    for meta in META_SKILLS:
        if meta not in mapping:
            s[meta]=_clamp(s.get(meta,0)+max(0.01,base_gain*0.35))
    brain["meta_learning"]["recent_lessons"]=(brain["meta_learning"].get("recent_lessons",[])+[
      {"day":day,"completed":completed,"failed":failed,"signal":round(signal,3)}
    ])[-50:]
    gaps=sorted(((k,float(v)) for k,v in s.items()),key=lambda x:x[1])[:5]
    brain["meta_learning"]["skill_gaps"]=[k for k,_ in gaps]
    brain["skill_history"].append({"day":day,"meta_avg":round(sum(s[k] for k in META_SKILLS)/len(META_SKILLS),3)})
    brain["skill_history"]=brain["skill_history"][-100:]


def plan_and_score(a, context=None):
    ensure(a); context=context or {}
    s=a["skills"]; traits=a["traits"]
    focus=float(traits.get("focus",.5)); discipline=float(traits.get("discipline",.5))
    # Capacity grows with planning/focus but stays bounded for runner stability.
    capacity=1+int(min(5, (float(s.get("planning",0))+float(s.get("focus",0)))/35))
    capacity=max(1,min(6,capacity))
    a["task_capacity"]=capacity
    a["multitasking_profile"]={"capacity":capacity,"focus":round(focus,3),"discipline":round(discipline,3)}
    risk=float(traits.get("risk_tolerance",.5))
    adaptability=float(s.get("adaptability",0))/100
    creativity=float(s.get("creativity",0))/100
    return {"capacity":capacity,"risk":risk,"adaptability":adaptability,"creativity":creativity}


def run(s):
    day=int(s.get("day",0) or 0)
    for a in s.get("agents",[]):
        if a.get("permanent_status") != "alive": continue
        ensure(a)
        learn_from_outcomes(a,day)
        plan_and_score(a)
    s["skill_engine"]={"meta_skills":META_SKILLS,"trait_model":TRAITS,"version":2}
