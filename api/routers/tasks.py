from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from api.database import get_db
from api.models import Task, User, Agent, Bid, Delivery, Review, AuditEvent
from api.schemas import (
    TaskCreate, TaskResponse, BidResponse, SelectAgentRequest,
    FundTaskRequest, DeliveryResponse, DeliveryCreate,
    ApproveTaskRequest, DisputeTaskRequest, ResolveDisputeRequest
)
from api.agents import generate_agent_bids
from api.ranking import calculate_bid_score
from api.verifier import execute_agent_job, verify_delivery_against_criteria
from api.blockchain import blockchain_adapter

router = APIRouter(prefix="/tasks", tags=["Tasks & Workflow"])

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    """Create a new digital task and open it for agent proposals."""
    # Ensure client user exists or create dummy client profile
    client = db.query(User).filter(User.wallet_address == task_in.client_wallet).first()
    if not client:
        client = User(
            wallet_address=task_in.client_wallet or "0x71C8363820F8031971300a20824b942f73AC2023",
            display_name="Demo Client"
        )
        db.add(client)
        db.commit()
        db.refresh(client)

    task = Task(
        client_id=client.id,
        title=task_in.title,
        description=task_in.description,
        task_type=task_in.task_type,
        budget=task_in.budget,
        currency=task_in.currency,
        deadline=task_in.deadline,
        acceptance_criteria=task_in.acceptance_criteria,
        dataset_url=task_in.dataset_url,
        status="OPEN"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    audit = AuditEvent(
        actor=client.wallet_address,
        entity_type="TASK",
        entity_id=task.id,
        action="CREATE_TASK",
        event_payload={"budget": task.budget, "deadline": str(task.deadline)}
    )
    db.add(audit)
    db.commit()

    return task

@router.get("", response_model=List[TaskResponse])
def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    task_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all marketplace tasks with optional state/type filters."""
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == status_filter.upper())
    if task_type:
        query = query.filter(Task.task_type == task_type)
    return query.order_by(Task.created_at.desc()).all()

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Retrieve full details of a single task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/bids", response_model=List[BidResponse])
def generate_bids_for_task(task_id: str, db: Session = Depends(get_db)):
    """Dispatch task to registered AI agents and compute transparent rankings."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "OPEN":
        # If bids already exist, return them
        existing_bids = db.query(Bid).filter(Bid.task_id == task_id).all()
        if existing_bids:
            return existing_bids
        raise HTTPException(status_code=400, detail=f"Cannot generate bids for task in state {task.status}")

    # Clear prior bids if re-triggering while OPEN
    db.query(Bid).filter(Bid.task_id == task_id).delete()

    agents = db.query(Agent).filter(Agent.active == True).all()
    if not agents:
        raise HTTPException(status_code=500, detail="No active agents found in the registry")

    raw_proposals = generate_agent_bids(task, agents)
    saved_bids = []

    for prop in raw_proposals:
        agent = prop["agent"]
        score, breakdown = calculate_bid_score(
            task=task,
            agent=agent,
            bid_amount_str=prop["amount"],
            eta_minutes=prop["eta_minutes"],
            capability_fit=prop["capability_match"]
        )

        bid = Bid(
            task_id=task.id,
            agent_id=agent.id,
            amount=prop["amount"],
            currency=prop["currency"],
            eta_minutes=prop["eta_minutes"],
            capability_match=prop["capability_match"],
            plan=prop["plan"],
            limitations=prop["limitations"],
            score=score,
            score_breakdown=breakdown,
            status="SUBMITTED"
        )
        db.add(bid)
        saved_bids.append(bid)

    db.commit()
    # Refresh and populate agent metadata
    for b in saved_bids:
        db.refresh(b)
        b.agent_name = b.agent.name
        b.agent_archetype = b.agent.archetype

    # Return sorted by score descending
    saved_bids.sort(key=lambda x: float(x.score), reverse=True)
    return saved_bids

@router.get("/{task_id}/bids", response_model=List[BidResponse])
def get_task_bids(task_id: str, db: Session = Depends(get_db)):
    """Retrieve all submitted bids for a task ordered by transparent ranking."""
    bids = db.query(Bid).filter(Bid.task_id == task_id).order_by(Bid.score.desc()).all()
    for b in bids:
        b.agent_name = b.agent.name
        b.agent_archetype = b.agent.archetype
    return bids

@router.post("/{task_id}/select-agent", response_model=TaskResponse)
def select_agent_bid(task_id: str, body: SelectAgentRequest, db: Session = Depends(get_db)):
    """Client selects winning agent bid. Transitions state from OPEN to ASSIGNED."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "OPEN":
        raise HTTPException(status_code=400, detail=f"Cannot select agent for task in state {task.status}")

    bid = db.query(Bid).filter(Bid.id == body.bid_id, Bid.task_id == task_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Selected bid not found for this task")

    # Update states
    bid.status = "ACCEPTED"
    task.selected_bid_id = bid.id
    task.status = "ASSIGNED"
    db.commit()
    db.refresh(task)

    audit = AuditEvent(
        actor=task.client.wallet_address,
        entity_type="TASK",
        entity_id=task.id,
        action="SELECT_AGENT",
        event_payload={"selected_bid_id": bid.id, "agent_id": bid.agent_id, "amount": bid.amount}
    )
    db.add(audit)
    db.commit()

    return task

@router.post("/{task_id}/fund", response_model=TaskResponse)
def fund_task_escrow(task_id: str, req: FundTaskRequest = None, db: Session = Depends(get_db)):
    """Client deposits agreed payment into escrow. Transitions from ASSIGNED to FUNDED."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "ASSIGNED":
        raise HTTPException(status_code=400, detail=f"Cannot fund task in state {task.status}. Must be ASSIGNED.")

    selected_bid = db.query(Bid).filter(Bid.id == task.selected_bid_id).first()
    amount = selected_bid.amount if selected_bid else task.budget

    # Record on-chain / simulated transaction
    blockchain_adapter.record_funding(
        db=db,
        task=task,
        client_address=task.client.wallet_address,
        amount_eth=amount,
        tx_hash=req.tx_hash if req else None
    )

    task.status = "FUNDED"
    db.commit()
    db.refresh(task)
    return task

@router.post("/{task_id}/execute", response_model=DeliveryResponse)
def execute_task_job(task_id: str, db: Session = Depends(get_db)):
    """Run assigned agent runner, execute data analysis, and record verified deliverable."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ["FUNDED", "IN_PROGRESS"]:
        raise HTTPException(status_code=400, detail=f"Task must be FUNDED before execution. Current: {task.status}")

    task.status = "IN_PROGRESS"
    db.commit()

    selected_bid = db.query(Bid).filter(Bid.id == task.selected_bid_id).first()
    agent = selected_bid.agent if selected_bid else db.query(Agent).first()

    # Execute bounded agent analysis
    execution_result = execute_agent_job(task, agent)
    
    # Run deterministic verifier against criteria
    verification = verify_delivery_against_criteria(
        task=task,
        delivery_data=execution_result,
        criteria=task.acceptance_criteria or []
    )

    # Persist or update delivery
    existing_delivery = db.query(Delivery).filter(Delivery.task_id == task_id).first()
    if existing_delivery:
        db.delete(existing_delivery)

    delivery = Delivery(
        task_id=task.id,
        agent_id=agent.id,
        result_uri=execution_result["result_uri"],
        result_hash=execution_result["result_hash"],
        summary=execution_result["summary"],
        output_data=execution_result["output_data"],
        verification_status=verification["status"],
        verification_report=verification
    )
    db.add(delivery)
    
    task.status = "DELIVERED"
    db.commit()
    db.refresh(delivery)
    return delivery

@router.post("/{task_id}/approve", response_model=TaskResponse)
def approve_delivery_and_settle(task_id: str, req: ApproveTaskRequest, db: Session = Depends(get_db)):
    """Client approves delivery; triggers escrow payout to agent and updates reputation."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "DELIVERED":
        raise HTTPException(status_code=400, detail=f"Cannot approve task in state {task.status}. Must be DELIVERED.")

    selected_bid = db.query(Bid).filter(Bid.id == task.selected_bid_id).first()
    agent = selected_bid.agent if selected_bid else db.query(Agent).first()
    amount = selected_bid.amount if selected_bid else task.budget

    # 1. Record on-chain settlement transaction
    blockchain_adapter.record_settlement(
        db=db,
        task=task,
        agent_address=agent.wallet_address,
        amount_eth=amount
    )

    # 2. Add review
    review = Review(
        task_id=task.id,
        reviewer_id=task.client_id,
        agent_id=agent.id,
        rating=req.feedback_rating,
        comments=req.comments,
        evidence_uri=task.delivery.result_uri if task.delivery else None
    )
    db.add(review)

    # 3. Update agent reputation
    current_settled = agent.settled_tasks_count or 0
    current_rep = float(agent.reputation_score or 4.5)
    new_rep = round((current_rep * current_settled + req.feedback_rating) / (current_settled + 1), 2)
    agent.settled_tasks_count = current_settled + 1
    agent.reputation_score = new_rep

    # 4. Mark task settled
    task.status = "SETTLED"
    db.commit()
    db.refresh(task)
    return task

@router.post("/{task_id}/dispute", response_model=TaskResponse)
def open_task_dispute(task_id: str, req: DisputeTaskRequest, db: Session = Depends(get_db)):
    """Open dispute for non-compliant delivery; halts automatic release."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ["IN_PROGRESS", "DELIVERED"]:
        raise HTTPException(status_code=400, detail=f"Cannot dispute task in state {task.status}")

    task.status = "DISPUTED"
    
    audit = AuditEvent(
        actor=task.client.wallet_address,
        entity_type="TASK",
        entity_id=task.id,
        action="OPEN_DISPUTE",
        event_payload={"reason": req.reason, "evidence_uri": req.evidence_uri}
    )
    db.add(audit)
    db.commit()
    db.refresh(task)
    return task

@router.post("/{task_id}/resolve-dispute", response_model=TaskResponse)
def resolve_task_dispute(task_id: str, req: ResolveDisputeRequest, db: Session = Depends(get_db)):
    """Reviewer/Admin resolves dispute on a task: PAY_AGENT, REFUND_CLIENT, or SPLIT_50_50."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "DISPUTED":
        raise HTTPException(status_code=400, detail=f"Cannot resolve task in state {task.status}. Must be DISPUTED.")

    selected_bid = db.query(Bid).filter(Bid.id == task.selected_bid_id).first()
    agent = selected_bid.agent if selected_bid else db.query(Agent).first()
    amount = selected_bid.amount if selected_bid else task.budget

    if req.outcome == "PAY_AGENT":
        blockchain_adapter.record_settlement(
            db=db,
            task=task,
            agent_address=agent.wallet_address,
            amount_eth=amount
        )
        task.status = "SETTLED"
    elif req.outcome == "REFUND_CLIENT":
        blockchain_adapter.record_refund(
            db=db,
            task=task,
            client_address=task.client.wallet_address,
            amount_eth=amount,
            reason=req.reviewer_notes or "Reviewer determined deliverable did not meet criteria."
        )
        task.status = "REFUNDED"
    elif req.outcome == "SPLIT_50_50":
        half_amount = str(round(float(amount) / 2.0, 4))
        blockchain_adapter.record_settlement(
            db=db,
            task=task,
            agent_address=agent.wallet_address,
            amount_eth=half_amount
        )
        blockchain_adapter.record_refund(
            db=db,
            task=task,
            client_address=task.client.wallet_address,
            amount_eth=half_amount,
            reason="Reviewer split escrow 50/50"
        )
        task.status = "SETTLED"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid outcome: {req.outcome}. Must be PAY_AGENT, REFUND_CLIENT, or SPLIT_50_50.")

    audit = AuditEvent(
        actor="AppointedReviewer",
        entity_type="TASK",
        entity_id=task.id,
        action="RESOLVE_DISPUTE",
        event_payload={"outcome": req.outcome, "reviewer_notes": req.reviewer_notes}
    )
    db.add(audit)
    db.commit()
    db.refresh(task)
    return task

