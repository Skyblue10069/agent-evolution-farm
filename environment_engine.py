"""Adaptive world for Agent Evolution.

The environment changes in response to verified activity and observed agent
behavior. It never creates fake revenue or fake customers; it only changes
simulation conditions and opportunity signals.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path

ROOT = Path(__file__).parent
WORLD_FILE = ROOT / "world_state.json"
OPP_FILE = ROOT / "opportunities.json"

DEFAULT = {
    "schema_version": 1,
    "day": 0,
    "market_cycle": 0,
    "conditions": {
        "competition": 0.35,
        "demand": 0.50,
        "opportunity_supply": 0.60,
        "resource_pressure": 0.25,
        "volatility": 0.20,
        "innovation_rate": 0.30,
    },
    "sectors": {},
    "events": [],
    "history": [],
}


def _load(path, fallback):
    try:
        return json.loads(path.read_text())
    except Exception:
        return fallback.copy()


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))


def load_world():
    w = _load(WORLD_FILE, DEFAULT)
    for k, v in DEFAULT["conditions"].items():
        w.setdefault("conditions", {}).setdefault(k, v)
    w.setdefault("sectors", {})
    w.setdefault("events", [])
    w.setdefault("history", [])
    return w


def _sector_for(opp):
    title = str(opp.get("title", "")).lower()
    tags = [str(x).lower() for x in opp.get("tags", [])]
    text = " ".join(tags + [title])
    for sector in ("software", "design", "writing", "marketing", "research", "education", "video", "engineering", "services"):
        if sector in text:
            return sector
    return "general"


def _agent_stats(agents):
    alive = [a for a in agents if a.get("permanent_status") == "alive"]
    pursued = sum(int(a.get("opportunities_pursued", 0) or 0) for a in alive)
    completed = sum(int(a.get("completed_work", 0) or 0) for a in alive)
    businesses = sum(len(a.get("businesses", []) or []) for a in alive)
    verified = sum(float(a.get("own_verified_revenue", 0) or 0) for a in alive)
    return len(alive), pursued, completed, businesses, verified


def evolve_world(state):
    world = load_world()
    day = int(state.get("day", 0))
    agents = state.get("agents", [])
    alive, pursued, completed, businesses, verified = _agent_stats(agents)
    opps = _load(OPP_FILE, {"opportunities": []}).get("opportunities", [])
    c = world["conditions"]

    # Population pressure makes competition rise gradually; successful work
    # increases demand and innovation. The response is bounded so the world
    # remains stable rather than exploding after one cycle.
    activity_ratio = _clamp(completed / max(1, alive * 2))
    pursuit_ratio = _clamp(pursued / max(1, alive * 2))
    business_ratio = _clamp(businesses / max(1, alive))
    c["competition"] = _clamp(c["competition"] + 0.018 * pursuit_ratio + 0.010 * business_ratio - 0.008 * (1 - pursuit_ratio))
    c["demand"] = _clamp(c["demand"] + 0.020 * activity_ratio - 0.012 * c["competition"] + random.uniform(-0.015, 0.015))
    c["resource_pressure"] = _clamp(c["resource_pressure"] + 0.014 * business_ratio + 0.010 * c["competition"] - 0.012 * activity_ratio)
    c["innovation_rate"] = _clamp(c["innovation_rate"] + 0.016 * activity_ratio - 0.006 * c["resource_pressure"] + random.uniform(-0.01, 0.01))
    c["volatility"] = _clamp(c["volatility"] + random.uniform(-0.018, 0.018) + 0.008 * c["competition"])
    c["opportunity_supply"] = _clamp(0.62 + 0.25 * c["demand"] + 0.18 * c["innovation_rate"] - 0.22 * c["competition"] - 0.12 * c["resource_pressure"])

    for opp in opps:
        sector = _sector_for(opp)
        sector_state = world["sectors"].setdefault(sector, {"demand": 0.5, "competition": 0.3, "trend": 0.0})
        sector_state["demand"] = _clamp(sector_state["demand"] + random.uniform(-0.025, 0.025) + 0.03 * (c["demand"] - 0.5))
        sector_state["competition"] = _clamp(sector_state["competition"] + 0.025 * c["competition"] - 0.01 * (sector_state["demand"] - 0.5))
        sector_state["trend"] = _clamp((sector_state["demand"] - sector_state["competition"] + 1) / 2)
        base = float(opp.get("score", 0) or 0)
        # Keep the original discovery score; expose an evolving environmental
        # score separately so discovery provenance is not overwritten.
        opp["environment_score"] = round(_clamp(0.5 * sector_state["trend"] + 0.3 * c["opportunity_supply"] + 0.2 * c["innovation_rate"]) * 100, 2)
        opp["environment"] = {"day": day, "sector": sector, "competition": round(sector_state["competition"], 4), "demand": round(sector_state["demand"], 4)}
        opp["score"] = round(max(0.0, min(100.0, 0.70 * base + 0.30 * float(opp["environment_score"]))))

    world["day"] = day
    world["market_cycle"] = int(world.get("market_cycle", 0)) + 1
    event = None
    if c["volatility"] > 0.70:
        event = {"type": "volatile_market", "effect": "higher_variance", "day": day}
    elif c["resource_pressure"] > 0.70:
        event = {"type": "resource_tightening", "effect": "harder_capacity", "day": day}
    elif c["innovation_rate"] > 0.72:
        event = {"type": "innovation_wave", "effect": "new_opportunity_signals", "day": day}
    if event:
        world["events"].append(event)
        world["events"] = world["events"][-100:]

    world["history"].append({"day": day, "conditions": {k: round(v, 4) for k, v in c.items()}, "alive": alive, "completed": completed, "businesses": businesses, "verified_xaf": round(verified, 2)})
    world["history"] = world["history"][-100:]
    WORLD_FILE.write_text(json.dumps(world, indent=2, sort_keys=True))
    OPP_FILE.write_text(json.dumps({"opportunities": opps}, indent=2, ensure_ascii=False))
    return world


if __name__ == "__main__":
    try:
        s = _load(ROOT / "state.json", {"day": 0, "agents": []})
        w = evolve_world(s)
        print("ENVIRONMENT EVOLVED", w["day"], w["conditions"])
    except Exception as exc:
        print("environment_engine:", exc)
