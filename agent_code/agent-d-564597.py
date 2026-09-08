"""Private strategy module owned by agent-d-564597."""

def score_bonus(context):
    """Return a small strategy bonus from 0.0 to 5.0."""
    skill_total = float(context.get("skill_total", 0.0) or 0.0)
    recent_success = float(context.get("recent_success", 0.0) or 0.0)
    return min(5.0, max(0.0, 0.205 + skill_total * 0.00086 + recent_success * 0.058))
