from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from api.database import get_db
from api.models import Transaction
from api.schemas import TransactionResponse

router = APIRouter(prefix="/transactions", tags=["Transactions & Escrow"])

@router.get("", response_model=List[TransactionResponse])
def list_transactions(limit: int = 50, db: Session = Depends(get_db)):
    """List recent on-chain escrow transactions across all tasks."""
    return db.query(Transaction).order_by(Transaction.confirmed_at.desc()).limit(limit).all()

@router.get("/{task_id}", response_model=List[TransactionResponse])
def get_task_transactions(task_id: str, db: Session = Depends(get_db)):
    """Retrieve on-chain transaction history (deposit, settlement, refund) for a specific task."""
    return db.query(Transaction).filter(Transaction.task_id == task_id).order_by(Transaction.confirmed_at.asc()).all()
