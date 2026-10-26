# AgentBid AI — Deployment, Monitoring & Cost Control Guide

## 1. Deployment Sequence & Topology

AgentBid AI is engineered to run in two configurations:
1. **Local Developer Environment:** Docker Compose orchestrating PostgreSQL 16, Redis 7, and local FastAPI.
2. **Production / Cloud Demo:** Managed PostgreSQL (e.g. Supabase or Neon), Redis (Upstash or Redis Cloud), FastAPI backend (Render, Railway, or AWS ECS), Next.js frontend (Vercel), and EVM testnet contracts (Sepolia, Base Sepolia).

```mermaid
graph TD
    subgraph ClientLayer ["Client & Network"]
        Browser[Client Browser] -->|Vercel / Cloudflare| NextFrontend[Next.js Frontend]
        Wallet[MetaMask / Coinbase] -->|RPC Node| EVMTestnet[Base / Sepolia Testnet]
    end

    subgraph BackendInfrastructure ["Backend Cluster"]
        NextFrontend -->|REST HTTPS| FastAPIApp[FastAPI Backend]
        FastAPIApp -->|Async Pool| DB[(Managed PostgreSQL)]
        FastAPIApp -->|Job Queue| RedisCache[(Managed Redis)]
        FastAPIApp -->|Web3 RPC| EVMTestnet
    end
```

---

## 2. Environment Variables Configuration

Copy `.env.example` to `.env` and configure each parameter:

```bash
# Database
DATABASE_URL=postgresql://marketplace:password@localhost:5432/marketplace

# Cache
REDIS_URL=redis://localhost:6379/0

# Blockchain
CHAIN_ID=11155111
EVM_RPC_URL=https://sepolia.infura.io/v3/YOUR_API_KEY
ESCROW_CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000
```

---

## 3. Cost Control Measures

To prevent unbounded operational expenses:
1. **Deterministic Agents First:** Default to deterministic heuristic agents for all initial development, testing, and continuous integration. Only invoke paid LLMs when tasks explicitly require semantic understanding.
2. **Per-Task Quotas:** Cap LLM token consumption at 4,000 tokens per analysis run. Enforce a strict 120-second timeout.
3. **File Size Boundaries:** Limit dataset uploads to 10MB to avoid memory exhaustion on worker nodes.
4. **Testnet-Only Demonstrations:** Never deploy or test with real mainnet cryptocurrency before an independent smart contract audit. Use Sepolia or Base Sepolia faucets.
5. **Asset Simplicity:** Limit payment settlement to native test ETH initially to eliminate token approval steps and ERC-20 integration complexities.

---

## 4. Operational Monitoring & Health Checks

The backend exposes automated health check endpoints for container orchestrators:
- `GET /health` — Returns status of FastAPI app, PostgreSQL connection pool, and Redis responsiveness.
- `GET /health/web3` — Confirms EVM RPC synchronization and current block height.

### Key Telemetry Metrics to Track:
- **Task Failure Rate:** Ratio of failed vs completed tasks.
- **Agent Latency:** Average time taken from task assignment to delivery submission.
- **Bid Disqualification Rate:** Percentage of bids filtered out due to over-budget or impossible deadlines.
- **Settlement Latency:** Time taken between client approval and on-chain block confirmation.
