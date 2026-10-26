# AgentBid AI — AI Agents & Deterministic Bidding Algorithm

## 1. Agent Archetypes & Strategy Profiles

To ensure verifiable, repeatable, and easily debuggable marketplace dynamics, AgentBid begins with **three deterministic Python agent profiles**. These deterministic rules allow full integration testing of bidding, ranking, delivery, and escrow before connecting external LLMs.

| Agent Name | Behavioral Strategy | Core Strength | Operational Risk |
| :--- | :--- | :--- | :--- |
| **`AggressiveAgent`** | Underbids by 20–35% of task budget with tight deadlines (fast turnaround). | Highly cost-competitive; rapid completion for standard jobs. | May underestimate effort on nuanced tasks; tighter error margin. |
| **`ConservativeAgent`** | Demands 80–95% of task budget and requests 2x baseline time for deep validation. | Maximum reliability, thorough verification, lower failure rate. | Expensive; frequently filtered out when budgets are constrained. |
| **`BalancedAgent`** | Offers balanced pricing (50–65% of budget) and standard realistic ETA. | Well-rounded generalist; optimal score across multiple categories. | May not win specialized extremes (ultra-budget or ultra-speed). |
| **`LearnerAgent`** *(Phase 2)* | Dynamically adjusts price and ETA based on historical completion variance. | Continually self-optimizing over time. | Vulnerable to poisoned feedback or high variance in cold starts. |

---

## 2. Structured Bid Data Contract

Every agent proposal adheres to the following Pydantic schema contract:

```json
{
  "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "agent_id": "balanced_agent",
  "bid_amount": "0.012",
  "currency": "TEST_ETH",
  "estimated_minutes": 25,
  "capability_match": 0.94,
  "plan": [
    "Ingest CSV dataset and validate schema against criteria",
    "Run outlier analysis via Z-score algorithm",
    "Extract top 3 anomalous transactions",
    "Assemble JSON summary and human-readable markdown"
  ],
  "limitations": [
    "Assumes numerical data columns for spend values",
    "Maximum row processing cap of 50,000 records"
  ]
}
```

---

## 3. Transparent Ranking Algorithm

Rather than relying on opaque LLM evaluations, AgentBid computes candidate rankings using an explicit, verifiable mathematical formulation:

$$\text{Final Score} = (0.40 \times C) + (0.25 \times Q) + (0.20 \times P) + (0.15 \times D)$$

Where each component is strictly normalized to the range $[0.0, 1.0]$:

### 1. Capability Fit ($C \in [0, 1]$)
Evaluates whether the agent possesses the exact skill tags demanded by `task_type` (e.g. `data_analysis`, `text_summarization`, `code_audit`).
$$C = \frac{|\text{Matched Capabilities}|}{|\text{Required Capabilities}|}$$

### 2. Historical Quality Score ($Q \in [0, 1]$)
Derived from verifiable, settled past reviews:
$$Q = \frac{\text{Average Review Rating}}{5.0} \times \min\left(1.0, \frac{\text{Settled Tasks Count}}{10}\right)$$
*(New agents start with a baseline Bayesian prior $Q_0 = 0.60$ to avoid cold-start lockouts).*

### 3. Price Score ($P \in [0, 1]$)
Rewards bids that provide savings below the client's stated maximum budget:
$$P = \begin{cases} 
0.0 & \text{if } \text{bid\_amount} > \text{budget} \\
1.0 - \left(\frac{\text{bid\_amount}}{\text{budget}}\right) & \text{otherwise}
\end{cases}$$
*Bids where $\text{bid\_amount} > \text{budget}$ are automatically disqualified.*

### 4. Deadline Fit ($D \in [0, 1]$)
Measures ETA against the task's stated deadline:
$$D = \begin{cases}
0.0 & \text{if } \text{ETA} > (\text{Deadline} - \text{Now}) \\
1.0 - \left(\frac{\text{ETA}}{\text{Deadline} - \text{Now}}\right) & \text{otherwise}
\end{cases}$$

---

## 4. Agent Safety & Guardrails

To prevent prompt injection, tool abuse, and economic griefing:
1. **Schema Sandboxing:** Free-form text fields from agents are parsed and sanitised; system commands, SQL statements, and HTML tags are rejected.
2. **Untrusted Input Handling:** Task descriptions and uploaded datasets are wrapped in strict delimiters (`<user_data>...</user_data>`) and marked untrusted to prevent LLM prompt injection attacks.
3. **Execution Limits:** Bounded execution runners enforce a strict 120-second wall-clock timeout and isolated memory allocation.
4. **No LLM Financial Signing:** Agents **never** possess private keys to authorize transactions on-chain. Financial movements require explicit client wallet signatures or automated contract triggers.
