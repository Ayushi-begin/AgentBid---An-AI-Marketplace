# AgentBid AI — Six-Week Implementation & Learning Roadmap

## 1. Overview & Daily Rhythm

This structured six-week roadmap provides a step-by-step path from empty repository to a fully functional AI agent marketplace integrated with testnet escrow settlement.

### Recommended Daily Rhythm (1–3 focused hours daily):
- **20 minutes:** Study core architectural concept from official documentation (FastAPI, Solidity, wagmi, Pydantic).
- **60–90 minutes:** Implement one focused, bounded feature or component.
- **20 minutes:** Write automated test cases and resolve regressions.
- **10 minutes:** Update documentation, commit clean diffs, and log demo progress.

---

## 2. Six-Week Milestone Breakdown

| Week | Phase | Study Focus | Build Deliverable | Exit Criterion |
| :---: | :--- | :--- | :--- | :--- |
| **Week 1** | **Foundation** | FastAPI async patterns, PostgreSQL schema design, Pydantic v2, REST design. | Core database models, migrations, Task CRUD API endpoints, local Docker setup. | Client can successfully create, retrieve, and filter tasks via API. |
| **Week 2** | **AI Agents** | Multi-agent coordination, deterministic heuristics, prompt sandboxing, async workers. | Implement `AggressiveAgent`, `ConservativeAgent`, and `BalancedAgent` with proposal generators. | Three distinct, structured proposals are generated for any valid task. |
| **Week 3** | **Ranking & Execution** | Normalization algorithms, scoring transparency, sandboxed data analysis runners. | Multi-factor bid scoring engine ($C, Q, P, D$), task execution runner, CSV outlier verifier. | System selects optimal winning agent with transparent score explanation and executes analysis. |
| **Week 4** | **Smart Contracts** | Solidity 0.8+, OpenZeppelin ReentrancyGuard, Foundry/Hardhat test suites. | Write `AgentBidEscrow.sol`, unit tests for state machine, edge cases, timeouts, reentrancy. | 100% test coverage on local EVM node for funding, delivery, payout, and refunds. |
| **Week 5** | **Integration** | EVM event listeners, Web3.py / viem RPC syncing, transaction reconciliation. | Connect Next.js dashboard, FastAPI backend, and testnet escrow contract with wallet signing. | Full end-to-end lifecycle runs on Sepolia/Base testnet with real-time UI updates. |
| **Week 6** | **Security & Demo** | Threat modeling, rate limiting, credential security, deployment packaging. | Docker Compose production readiness, demo script rehearsals, architectural walkthrough. | Clean, repeatable 2-minute demo with verifiable testnet transaction hashes. |

---

## 3. Definition of Done (DoD)

Before declaring the project complete, the following criteria must be satisfied:
1. **Zero-Setup Quickstart:** A new developer can clone the repo and run the full stack using `docker-compose up` or the local setup instructions.
2. **Automated Test Coverage:** Unit and integration tests cover the critical paths: Task creation $\rightarrow$ Bidding $\rightarrow$ Ranking $\rightarrow$ Escrow $\rightarrow$ Delivery $\rightarrow$ Settlement $\rightarrow$ Reputation.
3. **Consistent State Across Layers:** The database state, UI display, and smart contract state remain strictly synchronized.
4. **No Secrets in Version Control:** All API keys and private keys are isolated in local `.env` files.
5. **Decimal-Safe Financial Arithmetic:** No floating-point mathematical errors for escrowed funds.
