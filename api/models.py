import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from api.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    wallet_address = Column(String(42), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    tasks = relationship("Task", back_populates="client")
    reviews = relationship("Review", back_populates="reviewer")

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    archetype = Column(String(50), nullable=False, default="BALANCED")  # AGGRESSIVE, CONSERVATIVE, BALANCED
    description = Column(Text, nullable=True)
    capabilities = Column(JSON, default=list)  # ["data_analysis", "text_summarization"]
    pricing_config = Column(JSON, default=dict)
    wallet_address = Column(String(42), nullable=False)
    active = Column(Boolean, default=True, index=True)
    reputation_score = Column(Numeric(5, 2), default=4.50)  # e.g. 4.50 / 5.0
    settled_tasks_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    bids = relationship("Bid", back_populates="agent")
    deliveries = relationship("Delivery", back_populates="agent")
    reviews = relationship("Review", back_populates="agent")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    client_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    task_type = Column(String(50), nullable=False)  # "data_analysis", "text_summary", etc.
    budget = Column(String(50), nullable=False)  # decimal string to prevent float imprecision, e.g. "0.015"
    currency = Column(String(20), default="TEST_ETH", nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(30), default="OPEN", index=True)  # OPEN, ASSIGNED, FUNDED, IN_PROGRESS, DELIVERED, APPROVED, DISPUTED, SETTLED, REFUNDED, CANCELLED
    acceptance_criteria = Column(JSON, default=list)
    dataset_url = Column(String(500), nullable=True)
    selected_bid_id = Column(String(36), ForeignKey("bids.id", use_alter=True, name="fk_task_selected_bid"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    client = relationship("User", back_populates="tasks")
    bids = relationship("Bid", foreign_keys="Bid.task_id", back_populates="task", cascade="all, delete-orphan")
    delivery = relationship("Delivery", back_populates="task", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="task", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="task", cascade="all, delete-orphan")

class Bid(Base):
    __tablename__ = "bids"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    amount = Column(String(50), nullable=False)  # e.g. "0.012"
    currency = Column(String(20), default="TEST_ETH")
    eta_minutes = Column(Integer, nullable=False)
    capability_match = Column(Numeric(5, 4), default=0.0)
    plan = Column(JSON, default=list)
    limitations = Column(JSON, default=list)
    score = Column(Numeric(5, 4), default=0.0, index=True)
    score_breakdown = Column(JSON, default=dict)
    status = Column(String(30), default="SUBMITTED")  # SUBMITTED, ACCEPTED, REJECTED
    submitted_at = Column(DateTime(timezone=True), default=utc_now)

    task = relationship("Task", foreign_keys=[task_id], back_populates="bids")
    agent = relationship("Agent", back_populates="bids")

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), unique=True, nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    result_uri = Column(String(500), nullable=False)
    result_hash = Column(String(66), nullable=False, index=True)  # Keccak256 or SHA-256
    summary = Column(Text, nullable=True)
    output_data = Column(JSON, default=dict)
    verification_status = Column(String(30), default="PENDING")  # PENDING, PASSED, FAILED
    verification_report = Column(JSON, default=dict)
    submitted_at = Column(DateTime(timezone=True), default=utc_now)

    task = relationship("Task", back_populates="delivery")
    agent = relationship("Agent", back_populates="deliveries")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comments = Column(Text, nullable=True)
    evidence_uri = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    task = relationship("Task", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
    agent = relationship("Agent", back_populates="reviews")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    chain_id = Column(Integer, nullable=False)
    contract_address = Column(String(42), nullable=False)
    tx_hash = Column(String(66), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # TASK_CREATED, TASK_FUNDED, DELIVERED, SETTLED, REFUNDED, DISPUTED
    amount = Column(String(50), nullable=True)
    from_address = Column(String(42), nullable=True)
    to_address = Column(String(42), nullable=True)
    status = Column(String(30), default="CONFIRMED")  # PENDING, CONFIRMED, REVERTED
    block_number = Column(Integer, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), default=utc_now)

    task = relationship("Task", back_populates="transactions")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(50), nullable=False)
    event_payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
