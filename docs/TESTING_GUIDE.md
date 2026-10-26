# AgentBid AI — Testing & Acceptance Criteria Guide

## 1. Testing Philosophy

In an application combining AI decision-making with financial smart contracts, thorough testing is mandatory to prevent stuck funds or economic exploitation.

Testing is divided into three tiers:
1. **Deterministic Unit Tests:** Validate Pydantic models, scoring formulas, state transitions, and edge cases in isolation.
2. **Integration & Lifecycle Tests:** Verify the complete journey from task creation to bidding, assignment, simulated escrow, execution, delivery, and settlement.
3. **Smart Contract Verification:** Exhaustive EVM test cases verifying authorization, reentrancy resistance, refund timeouts, and dispute paths.

---

## 2. Test Matrix by Subsystem

| Subsystem | Target Test Cases | Expected Outcome |
| :--- | :--- | :--- |
| **Task API** | • Missing task title or description.<br>• Negative or zero budget value.<br>• Deadline configured in the past.<br>• Unsupported task type string. | Returns `422 Unprocessable Entity` or `400 Bad Request` with descriptive error payload. |
| **Agent Bidding** | • Agent returns malformed JSON.<br>• Bid amount exceeds task budget.<br>• ETA exceeds stated task deadline.<br>• Agent worker timeout (> 120s). | Ineligible bids rejected; malformed outputs caught by schema; worker timeout gracefully handled. |
| **Ranking Engine** | • Identical input values across consecutive runs.<br>• Bids violating hard criteria.<br>• Component weights sum check ($\sum w_i = 1.0$). | Deterministic output (same inputs $\rightarrow$ exact same scores); invalid bids disqualified. |
| **Task Execution** | • Empty input file or oversized CSV (> 10MB).<br>• Unsupported file MIME types.<br>• Prompt injection payload attempting command execution. | Execution safely aborted; sandbox constraints enforced; injection sanitized. |
| **Smart Contract** | • Unauthorized caller calls `approveAndPay()`.<br>• Attempting double payout on already settled task.<br>• Client claims refund before deadline expiration.<br>• Reentrancy exploit attempt on payout. | All invalid calls revert with specific error codes; reentrancy prevented by `ReentrancyGuard`. |
| **Web3 Integration** | • RPC network drops during event indexing.<br>• Reverted transaction in mempool.<br>• Duplicate event processing (idempotency). | Backend detects transaction revert; duplicate events ignored via unique transaction hash index. |

---

## 3. Running Automated Test Suites

### Running Python Backend Tests:
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run full test suite with verbose output
pytest -v

# Run specific unit test categories
pytest tests/test_tasks.py -v
pytest tests/test_ranking.py -v
pytest tests/test_agents.py -v
```

### Running Smart Contract Tests:
```bash
# Using Foundry
forge test -vvv

# Using Hardhat
npx hardhat test
```
