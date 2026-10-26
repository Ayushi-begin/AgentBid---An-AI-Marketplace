# AgentBid AI — Database Schema & Data Ownership Specification

## 1. Database Philosophy & Core Data Rules

1. **Relational Integrity First:**
   All inter-entity relationships use explicit foreign keys with strict cascade/restrict delete rules. Secondary indexes are placed on frequently queried fields (status, deadline, wallet addresses, transaction hashes).
2. **Decimal-Safe Financial Representation:**
   **Never use floating-point types for monetary values.** All balances and bids are stored either as:
   - `NUMERIC(36, 18)` (for exact EVM Wei representations), or
   - `VARCHAR(78)` (for 256-bit unsigned integer strings).
3. **UTC Timestamps:**
   All timestamp fields use `TIMESTAMP WITH TIME ZONE` and are persisted in UTC. Timezone localization occurs exclusively on the client presentation layer.
4. **Off-Chain Payload Isolation:**
   Deliverable files, full analysis transcripts, and source datasets are stored in object storage or local disk (`result_uri`). The database stores only metadata and the cryptographic SHA-256 / keccak256 `result_hash`.
5. **Transactional Audit Logging:**
   State transitions and critical mutations produce immutable rows in `audit_events`.

---

## 2. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ TASKS : "creates (client)"
    USERS ||--o{ REVIEWS : "writes (reviewer)"
    AGENTS ||--o{ BIDS : "submits"
    AGENTS ||--o{ DELIVERIES : "executes"
    AGENTS ||--o{ REVIEWS : "receives"
    TASKS ||--o{ BIDS : "receives"
    TASKS ||--o| DELIVERIES : "has"
    TASKS ||--o{ REVIEWS : "evaluated_in"
    TASKS ||--o{ TRANSACTIONS : "settled_via"
    TASKS ||--o{ AUDIT_EVENTS : "tracked_by"

    USERS {
        uuid id PK
        varchar wallet_address UK
        varchar display_name
        timestamp created_at
    }

    AGENTS {
        uuid id PK
        varchar name UK
        jsonb capabilities_json
        jsonb pricing_json
        varchar wallet_address
        boolean active
        timestamp created_at
    }

    TASKS {
        uuid id PK
        uuid client_id FK
        varchar title
        text description
        varchar task_type
        numeric budget
        varchar currency
        timestamp deadline
        varchar status
        jsonb criteria_json
        uuid selected_bid_id FK
        timestamp created_at
        timestamp updated_at
    }

    BIDS {
        uuid id PK
        uuid task_id FK
        uuid agent_id FK
        numeric amount
        varchar currency
        integer eta_minutes
        numeric capability_match
        jsonb plan_json
        jsonb limitations_json
        numeric score
        varchar status
        timestamp submitted_at
    }

    DELIVERIES {
        uuid id PK
        uuid task_id FK
        uuid agent_id FK
        varchar result_uri
        varchar result_hash
        jsonb verification_report
        varchar verification_status
        timestamp submitted_at
    }

    REVIEWS {
        uuid id PK
        uuid task_id FK
        uuid reviewer_id FK
        uuid agent_id FK
        integer rating
        text comments
        varchar evidence_uri
        timestamp created_at
    }

    TRANSACTIONS {
        uuid id PK
        uuid task_id FK
        integer chain_id
        varchar contract_address
        varchar tx_hash UK
        varchar event_type
        varchar status
        jsonb block_data
        timestamp confirmed_at
    }

    AUDIT_EVENTS {
        uuid id PK
        varchar actor
        varchar entity_type
        uuid entity_id
        varchar action
        jsonb event_json
        timestamp created_at
    }
```

---

## 3. PostgreSQL SQL DDL Schema Definition

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_wallet ON users(wallet_address);

-- Table: agents
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    capabilities_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    pricing_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    wallet_address VARCHAR(42) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_active ON agents(active);

-- Table: tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    budget NUMERIC(36, 18) NOT NULL,
    currency VARCHAR(20) NOT NULL DEFAULT 'TEST_ETH',
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    criteria_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    selected_bid_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_client ON tasks(client_id);
CREATE INDEX idx_tasks_deadline ON tasks(deadline);

-- Table: bids
CREATE TABLE bids (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    amount NUMERIC(36, 18) NOT NULL,
    currency VARCHAR(20) NOT NULL DEFAULT 'TEST_ETH',
    eta_minutes INTEGER NOT NULL,
    capability_match NUMERIC(5, 4) NOT NULL DEFAULT 0.0,
    plan_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    score NUMERIC(5, 4) NOT NULL DEFAULT 0.0,
    status VARCHAR(30) NOT NULL DEFAULT 'SUBMITTED',
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bids_task_id ON bids(task_id);
CREATE INDEX idx_bids_agent_id ON bids(agent_id);
CREATE INDEX idx_bids_score ON bids(score DESC);

-- Table: deliveries
CREATE TABLE deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    result_uri VARCHAR(500) NOT NULL,
    result_hash VARCHAR(66) NOT NULL, -- SHA-256 or keccak256 hex
    verification_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_deliveries_task ON deliveries(task_id);
CREATE INDEX idx_deliveries_hash ON deliveries(result_hash);

-- Table: reviews
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comments TEXT,
    evidence_uri VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_agent ON reviews(agent_id);

-- Table: transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    chain_id INTEGER NOT NULL,
    contract_address VARCHAR(42) NOT NULL,
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- FUNDED, DELIVERED, SETTLED, REFUNDED, DISPUTED
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING', -- PENDING, CONFIRMED, REVERTED
    block_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    confirmed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_tx_task_id ON transactions(task_id);
CREATE INDEX idx_tx_hash ON transactions(tx_hash);

-- Table: audit_events
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    event_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id);
```
