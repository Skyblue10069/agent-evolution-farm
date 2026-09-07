"""Bounded self-modification for Agent Evolution agents.

Each agent owns a private strategy module under agent_code/. Agents may improve only
that private strategy surface. Core safety, payment, accounting, orchestration and
security code is immutable to agents. Every candidate is syntax-checked before it
replaces the previous version; failed edits are rejected and the previous code stays.
"""
from __future__ import annotations
import ast, hashlib, json, random, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CODE_DIR = ROOT / "agent_code"
STATE_FILE = ROOT / "agent_code_state.json"
CODE_DIR.mkdir(exist_ok=True)

# Only this small function body is agent-editable. It returns a bounded score bonus.
TEMPLATE = '''"""Private strategy module owned by {agent_id}."""\n\ndef score_bonus(context):\n    """Return a small strategy bonus from 0.0 to 5.0."""\n    skill_total = float(context.get("skill_total", 0.0) or 0.0)\n    recent_success = float(context.get("recent_success", 0.0) or 0.0)\n    return min(5.0, max(0.0, {bias:.3f} + skill_total * {skill_weight:.5f} + recent_success * {success_weight:.3f}))\n'''

EDITABLE_MARKER = "def score_bonus(context):"


def _safe_id(agent):
    return str(agent.get("id", "agent")).replace("/", "-").replace("\\", "-")


def _path(agent_id):
    return CODE_DIR / f"{agent_id}.py"


def _load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"schema_version": 1, "agents": {}}


def _save_state(state):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(STATE_FILE)


def _valid_code(code: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(code)
        funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "score_bonus"]
        if len(funcs) != 1:
            return False, "score_bonus must be the only top-level function"
        # Restrict self-edited modules to literals, arithmetic, context.get, min/max,
        # and basic names. No imports, filesystem, subprocess, network, eval, exec, etc.
        banned = {"import", "from", "open", "exec", "eval", "compile", "__import__", "subprocess", "socket", "requests", "os", "sys", "pathlib"}
        allowed_calls={"min","max","float"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False, "imports are not allowed in agent-owned strategy code"
            if isinstance(node, ast.Name) and node.id in banned:
                return False, f"blocked name: {node.id}"
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return False, "dunder attributes are not allowed"
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in allowed_calls:
                    if not (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "context" and node.func.attr == "get"):
                        return False, "only min/max/float and context.get calls are allowed"
        return True, "ok"
    except SyntaxError as e:
        return False, f"syntax error: {e}"


def ensure_agent_code(agent, state):
    aid = _safe_id(agent)
    path = _path(aid)
    if path.exists():
        return path
    seed = random.Random(aid)
    code = TEMPLATE.format(
        agent_id=aid,
        bias=seed.uniform(0.0, 1.0),
        skill_weight=seed.uniform(0.0005, 0.003),
        success_weight=seed.uniform(0.05, 0.25),
    )
    path.write_text(code)
    state.setdefault("agents", {})[aid] = {
        "version": 1,
        "accepted_edits": 0,
        "rejected_edits": 0,
        "sha256": hashlib.sha256(code.encode()).hexdigest(),
    }
    return path



def _candidate(agent, context, current_code):
    # Evolution is deliberately bounded: small parameter mutations only.
    seed = f"{agent.get('id')}:{agent.get('days_active',0)}:{agent.get('wins',0)}:{agent.get('losses',0)}"
    rng = random.Random(seed)
    bias = rng.uniform(0.0, 1.0)
    skill_weight = rng.uniform(0.0005, 0.003)
    success_weight = rng.uniform(0.05, 0.25)
    return TEMPLATE.format(agent_id=_safe_id(agent), bias=bias, skill_weight=skill_weight, success_weight=success_weight)

def evolve_agent(agent, context, state):
    """Attempt one bounded self-edit; return an audit result."""
    path = ensure_agent_code(agent, state)
    current = path.read_text()
    candidate = _candidate(agent, context, current)
    ok, reason = _valid_code(candidate)
    rec = state.setdefault("agents", {}).setdefault(_safe_id(agent), {})
    if not ok:
        rec["rejected_edits"] = int(rec.get("rejected_edits", 0)) + 1
        return {"agent_id": agent.get("id"), "status": "rejected", "reason": reason}
    backup = path.with_suffix(".py.bak")
    shutil.copy2(path, backup)
    path.write_text(candidate)
    rec["version"] = int(rec.get("version", 1)) + 1
    rec["accepted_edits"] = int(rec.get("accepted_edits", 0)) + 1
    rec["sha256"] = hashlib.sha256(candidate.encode()).hexdigest()
    return {"agent_id": agent.get("id"), "status": "accepted", "version": rec["version"], "sha256": rec["sha256"]}



def score_bonus(agent, context=None):
    """Evaluate the agent's current private strategy with restricted builtins."""
    context=context or {}
    path=ensure_agent_code(agent, _load_state())
    code=path.read_text()
    env={"__builtins__":{"min":min,"max":max,"float":float}}
    try:
        exec(compile(code, str(path), "exec"), env, env)
        value=float(env["score_bonus"](context))
        return max(0.0, min(5.0, value))
    except Exception:
        return 0.0

def run(state, max_agents=100):
    """Give every agent the capability to self-edit while bounding per-cycle IO.

    The scheduler selects at most max_agents per cycle; over multiple cycles the
    whole population gets turns. This keeps a 7,777-agent farm practical.
    """
    agents=[a for a in state.get("agents", []) if a.get("permanent_status") == "alive"]
    if not agents:
        return []
    day=int(state.get("day",0) or 0)
    rng=random.Random(day)
    rng.shuffle(agents)
    selected=agents[:max(1,int(max_agents))]
    code_state=_load_state()
    results=[]
    for agent in selected:
        context={
            "skill_total": sum(float(v or 0) for v in agent.get("skills", {}).values()),
            "recent_success": float(agent.get("wins", 0) or 0),
        }
        result=evolve_agent(agent, context, code_state)
        agent.setdefault("brain", {}).setdefault("self_modification", []).append(result)
        agent["brain"]["self_modification"]=agent["brain"]["self_modification"][-10:]
        results.append(result)
    _save_state(code_state)
    return results


if __name__ == "__main__":
    print("agent_self_modification: ready")
