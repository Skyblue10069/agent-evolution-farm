"""Private strategy module owned by agent-e-746373."""

def score_bonus(context):
    """Return a small strategy bonus from 0.0 to 5.0."""
    skill_total = float(context.get("skill_total", 0.0) or 0.0)
    recent_success = float(context.get("recent_success", 0.0) or 0.0)
    return min(5.0, max(0.0, 0.716 + skill_total * 0.00153 + recent_success * 0.182))
