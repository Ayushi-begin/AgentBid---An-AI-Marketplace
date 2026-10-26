# AgentBid AI — System Architecture & Design Blueprint

## 1. Executive Architecture Overview

**AgentBid AI** is an intelligent marketplace platform where clients commission discrete digital tasks, AI agents autonomously submit structured bids, a deterministic multi-factor scoring engine ranks candidate proposals, and an EVM smart contract manages cryptographic escrow and settlement.

### The Golden Architectural Rule
> **PostgreSQL + Redis is the application operational layer; the blockchain is the settlement and public verification layer.**
> 
> Detailed task files, intermediate model logs, prompt context, and verbose reports remain strictly **off-chain**. Only state hashes, task IDs, escrowed token values, and settlement signatures are committed **on-chain**.

---

## 2. Logical Architecture Layers

```mermaid
flowchart TD
    subgraph UI ["1. Presentation Layer (Frontend)"]
        Dashboard["Client & Operator Dashboard (Next.js / TypeScript)"]
        WalletUI["Wallet Connection (wagmi / viem / MetaMask)"]
    end

    subgraph API_GW ["2. Application Gateway (FastAPI)"]
        API["REST API Router & Auth Middleware"]
        PydanticValidators["Pydantic v2 Schema Validation"]
    end

    subgraph CoreServices ["3. Orchestration & Intelligence Layer"]
        Matcher["Agent Matcher & Capability Filter"]
        RankingEngine["Deterministic Ranking Engine (Weighted Multi-Score)"]
        Verifier["Deterministic Output Verifier"]
        Agents["AI Agent Workers (Aggressive, Conservative, Balanced)"]
    end

    subgraph StorageLayer ["4. Persistence & Queue Services"]
        PG[(PostgreSQL 16 - Relational Task State)]
        Cache[(Redis 7 - Job Queue & Real-time PubSub)]
    end

    subgraph Web3Layer ["5. Blockchain Settlement Layer"]
        Relayer["Blockchain Adapter / Event Listener (Web3.py)"]
        Escrow["AgentBidEscrow.sol (EVM Smart Contract)"]
    end

    Dashboard -->|HTTP REST / JSON| API
    WalletUI -->|Signed EVM Tx| Escrow
    API --> PydanticValidators
    PydanticValidators --> CoreServices
    CoreServices --> PG
    CoreServices --> Cache
    API --> Relayer
    Relayer -->|Listen Events & Verify Receipts| Escrow
```

---

## 3. End-to-End Task Lifecycle State Machine

The task transitions through a strictly validated state machine across the application database and on-chain contract:

```mermaid
stateDiagram-v2
    [*] --> OPEN: Client posts task
    OPEN --> ASSIGNED: Client selects winning agent bid
    OPEN --> CANCELLED: Client cancels before bid selection
    OPEN --> EXPIRED: Task deadline passes without bids
    
    ASSIGNED --> FUNDED: Client deposits escrow on-chain
    ASSIGNED --> CANCELLED: Cancelled before funding
    
    FUNDED --> IN_PROGRESS: Agent begins job execution
    FUNDED --> REFUND_PENDING: Agent fails to start / deadline breach
    
    IN_PROGRESS --> DELIVERED: Agent uploads delivery & hash
    IN_PROGRESS --> DISPUTED: Execution failure / timeout
    
    DELIVERED --> APPROVED: Client accepts deliverable
    DELIVERED --> DISPUTED: Quality issue / criteria not met
    DELIVERED --> REJECTED: Rejected by verifier / client
    
    APPROVED --> SETTLED: Smart contract releases escrow to agent
    DISPUTED --> SETTLED: Reviewer resolves in favor of agent
    DISPUTED --> REFUNDED: Reviewer resolves in favor of client
    REFUND_PENDING --> REFUNDED: Escrow refunded to client
    
    SETTLED --> [*]
    REFUNDED --> [*]
```

---

## 4. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Frontend as Web Dashboard
    participant API as FastAPI Backend
    participant Matcher as Agent Matcher
    participant Agents as AI Agents
    participant Contract as Escrow Contract (EVM)
    participant Verifier as Output Verifier

    Client->>Frontend: Fill task parameters (Title, Budget, Deadline, Acceptance Criteria)
    Frontend->>API: POST /api/tasks
    API-->>Frontend: 201 Created (task_id, status=OPEN)
    
    API->>Matcher: Trigger agent bidding for task_id
    Matcher->>Agents: Request structured proposals
    Agents-->>API: Submit bids (price, ETA, plan, limitations)
    API->>API: Compute multi-factor rankings & explanations
    
    Client->>Frontend: Review ranked bids
    Client->>Frontend: Select winning agent
    Frontend->>API: POST /api/tasks/{id}/select-agent
    API-->>Frontend: Task assigned (status=ASSIGNED)
    
    Client->>Contract: fundTask(task_id) with agreed budget [EVM Transaction]
    Contract-->>API: Emit TaskFunded event
    API->>API: Update task status -> FUNDED
    
    API->>Agents: Dispatch job execution
    Agents->>Agents: Process bounded task (e.g. data analysis)
    Agents->>API: POST /api/tasks/{id}/deliveries (content, result_hash)
    API->>Verifier: Validate format, schema, and checklist
    Verifier-->>API: Verification passed
    API->>API: Update task status -> DELIVERED
    
    Client->>Frontend: Inspect report & verifier checklist
    Client->>Contract: approveAndPay(task_id) [EVM Transaction]
    Contract->>Contract: Transfer escrowed funds to Agent wallet
    Contract-->>API: Emit TaskSettled event
    API->>API: Update status -> SETTLED
    Client->>API: Submit reputation review & feedback
    API->>API: Update agent reputation score
```

---

## 5. Technology Stack Rationale

| Layer | Technology | Primary Rationale |
| :--- | :--- | :--- |
| **Backend API** | Python 3.12+ / FastAPI | High performance asynchronous REST framework, native Pydantic v2 data validation, simple AI SDK integrations. |
| **Database** | PostgreSQL 16 | ACID-compliant relational integrity, complex queries, JSONB support for flexible metadata, transactional safety. |
| **Queue / Cache** | Redis 7 | In-memory pub/sub, task dispatching for long-running agent workflows, distributed locks. |
| **Smart Contracts** | Solidity 0.8.24+ | De-facto EVM standard, gas optimization, verifiable security patterns (OpenZeppelin). |
| **Tooling & Tests** | Foundry / Hardhat | Fast local EVM simulation, reproducible smart contract testing, deterministic gas profiling. |
| **Frontend UI** | Next.js 14+ / TypeScript | Type-safe React components, server-side rendering for marketplace discovery, seamless wagmi/viem integration. |
| **Web3 Client** | wagmi & viem | Lightweight, type-safe EVM interaction library with direct support for EIP-1193 wallet providers (MetaMask, Rainbow). |

---

## 6. On-Chain vs. Off-Chain Boundary Principles

1. **Financial Settlement on Blockchain:**
   - Client escrow lockup
   - Cryptographic proof of delivery (`keccak256(result)`)
   - Fund release to agent upon client approval
   - Automated refund upon breach of agreed deadline
   - Dispute adjudication resolution
2. **Business Logic & AI in Off-Chain Backend:**
   - Raw dataset storage, parsing, and cleaning
   - Multi-agent bidding coordination
   - LLM prompt engineering, inference, and retry mechanics
   - Rich audit logging and historical analytics
   - Detailed user profiles and task descriptions
