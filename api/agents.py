import logging
import re
from decimal import Decimal
from typing import Dict, Any, List
from api.models import Task, Agent

logger = logging.getLogger(__name__)

# Sanitization helper to guard against prompt injection
def sanitize_prompt_content(content: str) -> str:
    """Strip dangerous characters or suspicious instruction injections."""
    sanitized = re.sub(r"[<>{}\\]", "", content)
    return sanitized.strip()

class BaseAgentRunner:
    def __init__(self, agent_model: Agent):
        self.agent = agent_model

    def evaluate_task(self, task: Task) -> Dict[str, Any] | None:
        raise NotImplementedError

class AggressiveAgentRunner(BaseAgentRunner):
    """
    Aggressive Strategy:
    - Highly competitive price: ~65% of client's max budget.
    - Fast turnaround: ~15 minutes.
    - Strengths: Cost & speed.
    - Limitations: Minimal error buffering.
    """
    def evaluate_task(self, task: Task) -> Dict[str, Any] | None:
        budget = Decimal(task.budget)
        bid_amount = str(round(budget * Decimal("0.65"), 4))
        eta = 15

        # Check capability fit
        capabilities = self.agent.capabilities or ["data_analysis", "text_summary"]
        fit = 0.95 if task.task_type in capabilities else 0.50

        plan = [
            "Fast stream-parsing of input dataset",
            "Vectorized statistical aggregation via NumPy",
            "Rapid anomaly threshold extraction (Z > 3.0)",
            "Automated summary report generation"
        ]
        limitations = [
            "Optimized for speed; maximum file size 25MB",
            "Applies standard normal distribution heuristics"
        ]

        return {
            "amount": bid_amount,
            "currency": task.currency,
            "eta_minutes": eta,
            "capability_match": fit,
            "plan": plan,
            "limitations": limitations
        }

class ConservativeAgentRunner(BaseAgentRunner):
    """
    Conservative Strategy:
    - Premium price: ~92% of client's max budget.
    - Generous margin ETA: ~50 minutes.
    - Strengths: Thorough validation, multi-pass checks.
    """
    def evaluate_task(self, task: Task) -> Dict[str, Any] | None:
        budget = Decimal(task.budget)
        bid_amount = str(round(budget * Decimal("0.92"), 4))
        eta = 50

        capabilities = self.agent.capabilities or ["data_analysis", "code_audit"]
        fit = 0.98 if task.task_type in capabilities else 0.40

        plan = [
            "Comprehensive input validation and schema assertion",
            "Multi-pass statistical and IQR outlier verification",
            "Manual-equivalent cross-validation of results",
            "In-depth narrative report with boundary caveats"
        ]
        limitations = [
            "Requires well-structured schema",
            "Longer processing time for exhaustive verification"
        ]

        return {
            "amount": bid_amount,
            "currency": task.currency,
            "eta_minutes": eta,
            "capability_match": fit,
            "plan": plan,
            "limitations": limitations
        }

class BalancedAgentRunner(BaseAgentRunner):
    """
    Balanced Strategy:
    - Fair market price: ~78% of client's max budget.
    - Balanced ETA: ~25 minutes.
    - Optimal blend of speed, quality, and cost.
    """
    def evaluate_task(self, task: Task) -> Dict[str, Any] | None:
        budget = Decimal(task.budget)
        bid_amount = str(round(budget * Decimal("0.78"), 4))
        eta = 25

        capabilities = self.agent.capabilities or ["data_analysis", "text_summary", "code_audit"]
        fit = 0.92 if task.task_type in capabilities else 0.60

        plan = [
            "Ingest dataset and validate acceptance criteria checklist",
            "Calculate descriptive statistics & detect anomalous records",
            "Structure output into machine-readable JSON & executive markdown",
            "Perform automated self-check prior to delivery"
        ]
        limitations = [
            "Requires standard numerical data fields",
            "Standard precision bounds"
        ]

        return {
            "amount": bid_amount,
            "currency": task.currency,
            "eta_minutes": eta,
            "capability_match": fit,
            "plan": plan,
            "limitations": limitations
        }

def get_agent_runner(agent: Agent) -> BaseAgentRunner:
    archetype = (agent.archetype or "BALANCED").upper()
    if archetype == "AGGRESSIVE":
        return AggressiveAgentRunner(agent)
    elif archetype == "CONSERVATIVE":
        return ConservativeAgentRunner(agent)
    return BalancedAgentRunner(agent)

def generate_agent_bids(task: Task, agents: List[Agent]) -> List[Dict[str, Any]]:
    """Dispatch task to candidate agents and return structured bid dictionaries."""
    proposals = []
    for agent in agents:
        if not agent.active:
            continue
        runner = get_agent_runner(agent)
        bid_data = runner.evaluate_task(task)
        if bid_data:
            proposals.append({
                "agent_id": agent.id,
                "agent": agent,
                **bid_data
            })
    return proposals
