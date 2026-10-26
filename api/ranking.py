from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from api.models import Task, Agent

# Configured Transparent Weights (sum = 1.0)
WEIGHT_CAPABILITY = Decimal("0.40")
WEIGHT_QUALITY = Decimal("0.25")
WEIGHT_PRICE = Decimal("0.20")
WEIGHT_DEADLINE = Decimal("0.15")

def calculate_bid_score(
    task: Task,
    agent: Agent,
    bid_amount_str: str,
    eta_minutes: int,
    capability_fit: float
) -> Tuple[float, Dict[str, Any]]:
    """
    Transparent Multi-Factor Ranking Formula:
    Score = 0.40 * Capability + 0.25 * Quality + 0.20 * Price + 0.15 * Deadline
    Returns (final_score, breakdown_dict)
    """
    task_budget = Decimal(task.budget)
    bid_amount = Decimal(bid_amount_str)

    # 1. Capability Score (0..1)
    c_score = Decimal(str(capability_fit))
    c_score = max(Decimal("0.0"), min(Decimal("1.0"), c_score))

    # 2. Historical Quality Score (0..1)
    rep = Decimal(str(agent.reputation_score or 4.5))
    settled = agent.settled_tasks_count or 0
    # Normalize reputation to 0..1 scale with prior damping for new agents
    rep_normalized = rep / Decimal("5.0")
    confidence_factor = Decimal(str(min(1.0, max(0.5, settled / 10.0))))
    q_score = rep_normalized * confidence_factor
    q_score = max(Decimal("0.0"), min(Decimal("1.0"), q_score))

    # 3. Price Score (0..1)
    # Lower price relative to budget yields higher score
    if bid_amount > task_budget:
        p_score = Decimal("0.0")  # Over budget bids get 0 price score
    else:
        p_score = Decimal("1.0") - (bid_amount / task_budget)
        p_score = max(Decimal("0.0"), min(Decimal("1.0"), p_score))

    # 4. Deadline Fit (0..1)
    # ETA compared against available time until task deadline
    now = datetime.now(timezone.utc)
    # Ensure task.deadline is timezone aware
    task_deadline = task.deadline
    if task_deadline.tzinfo is None:
        task_deadline = task_deadline.replace(tzinfo=timezone.utc)
        
    time_left_seconds = (task_deadline - now).total_seconds()
    available_minutes = max(15.0, time_left_seconds / 60.0)

    if eta_minutes > available_minutes:
        d_score = Decimal("0.0")
    else:
        d_score = Decimal("1.0") - (Decimal(str(eta_minutes)) / Decimal(str(available_minutes)))
        d_score = max(Decimal("0.0"), min(Decimal("1.0"), d_score))

    # Weighted Sum
    component_c = WEIGHT_CAPABILITY * c_score
    component_q = WEIGHT_QUALITY * q_score
    component_p = WEIGHT_PRICE * p_score
    component_d = WEIGHT_DEADLINE * d_score

    final_score = component_c + component_q + component_p + component_d
    final_score_float = round(float(final_score), 4)

    breakdown = {
        "capability_component": round(float(component_c), 4),
        "quality_component": round(float(component_q), 4),
        "price_component": round(float(component_p), 4),
        "deadline_component": round(float(component_d), 4),
        "raw_metrics": {
            "capability_fit": float(c_score),
            "reputation_rating": float(rep),
            "bid_amount": str(bid_amount),
            "eta_minutes": eta_minutes
        },
        "weights": {
            "capability": float(WEIGHT_CAPABILITY),
            "quality": float(WEIGHT_QUALITY),
            "price": float(WEIGHT_PRICE),
            "deadline": float(WEIGHT_DEADLINE)
        }
    }

    return final_score_float, breakdown
