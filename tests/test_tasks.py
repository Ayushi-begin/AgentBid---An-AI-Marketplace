import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from api.main import app
from api.database import SessionLocal, Base, engine
from api.models import Agent

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Ensure default agents exist
    if db.query(Agent).count() == 0:
        db.add_all([
            Agent(
                name="TestAggressive",
                archetype="AGGRESSIVE",
                capabilities=["data_analysis"],
                wallet_address="0x1111111111111111111111111111111111111111",
                reputation_score=4.4,
                settled_tasks_count=10
            ),
            Agent(
                name="TestBalanced",
                archetype="BALANCED",
                capabilities=["data_analysis"],
                wallet_address="0x2222222222222222222222222222222222222222",
                reputation_score=4.8,
                settled_tasks_count=20
            ),
            Agent(
                name="TestConservative",
                archetype="CONSERVATIVE",
                capabilities=["data_analysis"],
                wallet_address="0x3333333333333333333333333333333333333333",
                reputation_score=4.9,
                settled_tasks_count=15
            )
        ])
        db.commit()
    db.close()
    yield

def test_create_task_success():
    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    payload = {
        "title": "Analyze CSV Outliers Test",
        "task_type": "data_analysis",
        "description": "Scan 1,000 transactions and report top anomalies.",
        "budget": "0.020",
        "currency": "TEST_ETH",
        "deadline": deadline,
        "acceptance_criteria": ["Find at least 3 anomalies", "Include summary statistics"],
        "dataset_url": "test_dataset.csv",
        "client_wallet": "0x71C8363820F8031971300a20824b942f73AC2023"
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["status"] == "OPEN"
    assert "id" in data

def test_create_task_invalid_budget():
    deadline = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {
        "title": "Invalid Negative Budget Task",
        "task_type": "data_analysis",
        "description": "This should fail validation.",
        "budget": "-0.05",
        "currency": "TEST_ETH",
        "deadline": deadline,
        "acceptance_criteria": ["Criteria 1"]
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 422

def test_full_task_lifecycle_workflow():
    # 1. Create Task
    deadline = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_res = client.post("/api/tasks", json={
        "title": "Lifecycle End-to-End Test",
        "task_type": "data_analysis",
        "description": "Complete lifecycle from bidding to settlement.",
        "budget": "0.015",
        "currency": "TEST_ETH",
        "deadline": deadline,
        "acceptance_criteria": ["Find 3 anomalies", "Valid JSON report"]
    })
    assert create_res.status_code == 201
    task_id = create_res.json()["id"]

    # 2. Trigger Bidding
    bids_res = client.post(f"/api/tasks/{task_id}/bids")
    assert bids_res.status_code == 200
    bids = bids_res.json()
    assert len(bids) >= 3
    # Top bid should have highest score
    assert float(bids[0]["score"]) >= float(bids[1]["score"])
    top_bid_id = bids[0]["id"]

    # 3. Select Winning Bid
    select_res = client.post(f"/api/tasks/{task_id}/select-agent", json={"bid_id": top_bid_id})
    assert select_res.status_code == 200
    assert select_res.json()["status"] == "ASSIGNED"

    # 4. Fund Escrow
    fund_res = client.post(f"/api/tasks/{task_id}/fund")
    assert fund_res.status_code == 200
    assert fund_res.json()["status"] == "FUNDED"

    # 5. Execute Task Job
    exec_res = client.post(f"/api/tasks/{task_id}/execute")
    assert exec_res.status_code == 200
    delivery = exec_res.json()
    assert delivery["verification_status"] == "PASSED"
    assert delivery["result_hash"].startswith("0x")

    # 6. Approve & Settle
    approve_res = client.post(f"/api/tasks/{task_id}/approve", json={
        "feedback_rating": 5,
        "comments": "Great work on the anomalies analysis."
    })
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "SETTLED"

    # 7. Check Blockchain Transactions
    tx_res = client.get(f"/api/transactions/{task_id}")
    assert tx_res.status_code == 200
    txs = tx_res.json()
    assert len(txs) >= 2  # TASK_FUNDED and SETTLED

def test_service_provider_agent_registration():
    import uuid
    unique_name = f"ProviderAgent_{uuid.uuid4().hex[:6]}"
    payload = {
        "name": unique_name,
        "archetype": "BALANCED",
        "description": "Provider-registered custom AI agent",
        "capabilities": ["data_analysis", "code_audit"],
        "wallet_address": "0x5555555555555555555555555555555555555555"
    }
    res = client.post("/api/agents", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["wallet_address"] == payload["wallet_address"]

def test_dispute_and_reviewer_arbitration():
    # Create and fund a task
    deadline = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    t = client.post("/api/tasks", json={
        "title": "Dispute Test Task",
        "task_type": "data_analysis",
        "description": "Dispute flow testing.",
        "budget": "0.010",
        "currency": "TEST_ETH",
        "deadline": deadline,
        "acceptance_criteria": ["Check 1"]
    }).json()
    task_id = t["id"]

    # Bids & Select
    bids = client.post(f"/api/tasks/{task_id}/bids").json()
    client.post(f"/api/tasks/{task_id}/select-agent", json={"bid_id": bids[0]["id"]})
    client.post(f"/api/tasks/{task_id}/fund")
    client.post(f"/api/tasks/{task_id}/execute")

    # Client opens dispute
    disp_res = client.post(f"/api/tasks/{task_id}/dispute", json={
        "reason": "Anomalies missing column references."
    })
    assert disp_res.status_code == 200
    assert disp_res.json()["status"] == "DISPUTED"

    # Reviewer resolves dispute
    resolve_res = client.post(f"/api/tasks/{task_id}/resolve-dispute", json={
        "outcome": "SPLIT_50_50",
        "reviewer_notes": "Reviewed evidence: partial completion granted."
    })
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "SETTLED"

