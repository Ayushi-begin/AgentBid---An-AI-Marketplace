from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

# --- User Schemas ---
class UserBase(BaseModel):
    wallet_address: str = Field(..., example="0x71C8363820F8031971300a20824b942f73AC2023")
    display_name: Optional[str] = Field(None, example="Alice (Data Scientist)")

class UserResponse(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Agent Schemas ---
class AgentResponse(BaseModel):
    id: str
    name: str
    archetype: str
    description: Optional[str] = None
    capabilities: List[str]
    wallet_address: str
    active: bool
    reputation_score: float
    settled_tasks_count: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Task Schemas ---
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255, example="Analyze a CSV dataset and detect anomalies")
    task_type: str = Field(..., example="data_analysis")
    description: str = Field(..., min_length=10, example="Examine the dataset, calculate descriptive stats, find top 3 anomalies.")
    budget: str = Field(..., example="0.015", description="Agreed maximum budget in ETH")
    currency: str = Field("TEST_ETH", example="TEST_ETH")
    deadline: datetime = Field(..., description="UTC deadline")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        example=[
            "Return top 3 detected anomalies with row indices",
            "Provide clear descriptive statistics summary",
            "Return valid JSON structure plus markdown report"
        ]
    )
    dataset_url: Optional[str] = Field(None, example="https://raw.githubusercontent.com/datasets/sample.csv")
    client_wallet: Optional[str] = Field("0x71C8363820F8031971300a20824b942f73AC2023")

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: str) -> str:
        try:
            val = Decimal(v)
            if val <= 0:
                raise ValueError("Budget must be strictly positive.")
        except Exception:
            raise ValueError("Budget must be a valid positive numeric decimal string.")
        return v

class TaskResponse(BaseModel):
    id: str
    client_id: str
    title: str
    description: str
    task_type: str
    budget: str
    currency: str
    deadline: datetime
    status: str
    acceptance_criteria: List[str]
    dataset_url: Optional[str] = None
    selected_bid_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Bid Schemas ---
class BidResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    agent_name: Optional[str] = None
    agent_archetype: Optional[str] = None
    amount: str
    currency: str
    eta_minutes: int
    capability_match: float
    plan: List[str]
    limitations: List[str]
    score: float
    score_breakdown: Dict[str, Any]
    status: str
    submitted_at: datetime

    class Config:
        from_attributes = True

class SelectAgentRequest(BaseModel):
    bid_id: str

class FundTaskRequest(BaseModel):
    tx_hash: Optional[str] = None
    amount: Optional[str] = None

# --- Delivery Schemas ---
class DeliveryCreate(BaseModel):
    result_uri: str = Field(..., example="s3://agentbid-storage/task_output.json")
    summary: Optional[str] = Field(None, example="Processed 5,000 rows. Found 3 anomalies.")
    output_data: Dict[str, Any] = Field(default_factory=dict)

class DeliveryResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    result_uri: str
    result_hash: str
    summary: Optional[str]
    output_data: Dict[str, Any]
    verification_status: str
    verification_report: Dict[str, Any]
    submitted_at: datetime

    class Config:
        from_attributes = True

# --- Review & Dispute Schemas ---
class ApproveTaskRequest(BaseModel):
    feedback_rating: int = Field(5, ge=1, le=5)
    comments: Optional[str] = Field(None, example="Excellent execution ahead of time.")

class DisputeTaskRequest(BaseModel):
    reason: str = Field(..., min_length=5, example="Output is missing key required anomaly columns.")
    evidence_uri: Optional[str] = None

# --- Transaction Schemas ---
class TransactionResponse(BaseModel):
    id: str
    task_id: str
    chain_id: int
    contract_address: str
    tx_hash: str
    event_type: str
    amount: Optional[str]
    from_address: Optional[str]
    to_address: Optional[str]
    status: str
    block_number: Optional[int]
    confirmed_at: datetime

    class Config:
        from_attributes = True
