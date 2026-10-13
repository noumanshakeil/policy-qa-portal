from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db import get_db
from backend.services import policies as svc

class PolicyIn(BaseModel):
    title: str = Field(min_length=2)
    body: str = Field(min_length=20)
    category: str = "hr"
    version: str = "1.0"

class AskIn(BaseModel):
    question: str = Field(min_length=3)
    category: str | None = None

router = APIRouter()

@router.get("/policies")
async def list_policies(category: str | None = None, db: AsyncSession = Depends(get_db)):
    rows = await svc.list_policies(db, category)
    return {
        "policies": [
            {"id": p.id, "title": p.title, "category": p.category, "version": p.version}
            for p in rows
        ]
    }

@router.post("/policies")
async def create(payload: PolicyIn, db: AsyncSession = Depends(get_db)):
    return await svc.publish(db, payload.title, payload.body, payload.category, payload.version)

@router.post("/ask")
async def ask(payload: AskIn, db: AsyncSession = Depends(get_db)):
    return await svc.ask(db, payload.question, payload.category)
