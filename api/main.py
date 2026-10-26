import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.config import settings
from api.database import engine, Base, SessionLocal
from api.models import Agent
from api.routers import tasks, agents, transactions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentBid")

def seed_default_agents():
    """Seed the default 3 deterministic agents into the registry if empty."""
    db = SessionLocal()
    try:
        count = db.query(Agent).count()
        if count == 0:
            logger.info("Seeding default 3 AI agents into registry...")
            default_agents = [
                Agent(
                    name="AggressiveAgent-Alpha",
                    archetype="AGGRESSIVE",
                    description="High-velocity, price-competitive agent optimized for rapid throughput on bounded datasets.",
                    capabilities=["data_analysis", "text_summary", "data_extraction"],
                    wallet_address="0x1111111111111111111111111111111111111111",
                    reputation_score=4.40,
                    settled_tasks_count=18,
                    active=True
                ),
                Agent(
                    name="BalancedAgent-Prime",
                    archetype="BALANCED",
                    description="Optimal generalist balancing competitive market pricing, thorough verification, and reliable delivery.",
                    capabilities=["data_analysis", "text_summary", "code_audit", "classification"],
                    wallet_address="0x2222222222222222222222222222222222222222",
                    reputation_score=4.85,
                    settled_tasks_count=42,
                    active=True
                ),
                Agent(
                    name="ConservativeAgent-Sentinel",
                    archetype="CONSERVATIVE",
                    description="High-assurance, exhaustive auditing agent. Demands premium budgets and extra time for rigorous checks.",
                    capabilities=["data_analysis", "code_audit", "security_review"],
                    wallet_address="0x3333333333333333333333333333333333333333",
                    reputation_score=4.95,
                    settled_tasks_count=29,
                    active=True
                )
            ]
            db.add_all(default_agents)
            db.commit()
            logger.info("Seeded 3 default agents successfully.")
    except Exception as e:
        logger.error(f"Error seeding default agents: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas
    try:
        Base.metadata.create_all(bind=engine)
        seed_default_agents()
    except Exception as e:
        logger.error(f"Database startup error: {e}")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Decentralized AI Agent Marketplace with Escrow & Verifiable Reputation",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(tasks.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")

# Static files for web dashboard
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def home():
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "chain_id": settings.CHAIN_ID,
        "escrow_contract": settings.ESCROW_CONTRACT_ADDRESS
    }