import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "AgentBid AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database Settings
    # Supports PostgreSQL or fallback SQLite for zero-friction local testing
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agentbid.db")
    
    # Redis Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Blockchain / Escrow Settings
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "11155111"))  # Sepolia
    EVM_RPC_URL: str = os.getenv("EVM_RPC_URL", "https://rpc.sepolia.org")
    ESCROW_CONTRACT_ADDRESS: str = os.getenv("ESCROW_CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
    
    # Security
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")
    
    @property
    def cors_origins(self) -> List[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
