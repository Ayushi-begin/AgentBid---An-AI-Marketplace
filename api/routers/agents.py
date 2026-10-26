from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from api.database import get_db
from api.models import Agent, Task, Bid, Transaction
from api.schemas import AgentResponse, AgentCreateRequest

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("", response_model=List[AgentResponse])
def list_registered_agents(db: Session = Depends(get_db)):
    """List all registered AI agents with capabilities and verified reputation."""
    return db.query(Agent).filter(Agent.active == True).order_by(Agent.reputation_score.desc()).all()

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def register_new_agent(req: AgentCreateRequest, db: Session = Depends(get_db)):
    """Service Provider registers a new AI Agent to discover tasks and bid in the marketplace."""
    existing = db.query(Agent).filter(Agent.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Agent with name '{req.name}' already exists.")

    agent = Agent(
        name=req.name,
        archetype=req.archetype.upper(),
        description=req.description or f"Autonomous agent specialized in {', '.join(req.capabilities)}",
        capabilities=req.capabilities,
        wallet_address=req.wallet_address,
        reputation_score=4.50,  # Bayesian prior for initial reputation
        settled_tasks_count=0,
        active=True
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Retrieve full details of an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("/{agent_id}/provider-metrics")
def get_provider_agent_metrics(agent_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Fetch earnings, won tasks, and bidding performance for a service provider's agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    total_bids = db.query(Bid).filter(Bid.agent_id == agent_id).count()
    won_tasks = db.query(Task).join(Bid, Task.selected_bid_id == Bid.id).filter(Bid.agent_id == agent_id).all()
    
    # Calculate earnings from settled transactions
    settled_txs = db.query(Transaction).filter(
        Transaction.to_address == agent.wallet_address,
        Transaction.event_type == "SETTLED"
    ).all()
    
    total_earned_eth = sum(float(tx.amount or 0) for tx in settled_txs)

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "wallet_address": agent.wallet_address,
        "reputation_score": float(agent.reputation_score),
        "total_bids_submitted": total_bids,
        "jobs_won_count": len(won_tasks),
        "settled_tasks_count": agent.settled_tasks_count,
        "total_earned_eth": round(total_earned_eth, 4),
        "recent_jobs": [
            {
                "task_id": t.id,
                "title": t.title,
                "status": t.status,
                "budget": t.budget,
                "created_at": str(t.created_at)
            }
            for t in won_tasks[:10]
        ]
    }
