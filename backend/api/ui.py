from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db import get_db
from backend.services import policies as svc

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, category: str | None = None, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Policy Q&A Portal",
            "category": category or "",
            "policies": await svc.list_policies(db, category or None),
            "answer": None,
            "citations": [],
        },
    )

@router.post("/ui/policies")
async def ui_pub(
    title: str = Form(...),
    body: str = Form(...),
    category: str = Form("hr"),
    version: str = Form("1.0"),
    db: AsyncSession = Depends(get_db),
):
    await svc.publish(db, title, body, category, version)
    return RedirectResponse(f"/?category={category}", status_code=303)

@router.post("/ui/ask", response_class=HTMLResponse)
async def ui_ask(
    request: Request,
    question: str = Form(...),
    category: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    cat = category or None
    result = await svc.ask(db, question, cat)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Policy Q&A Portal",
            "category": category,
            "policies": await svc.list_policies(db, cat),
            "answer": result["answer"],
            "citations": result["citations"],
            "question": question,
        },
    )
