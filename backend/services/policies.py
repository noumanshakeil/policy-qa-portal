from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.llm import get_llm
from backend.models import Policy, PolicyChunk
from backend.services.rag_core import Hit, chunk_text, pack_citations, score_chunk


async def publish(
    session: AsyncSession, title: str, body: str, category: str = "hr", version: str = "1.0"
) -> dict:
    policy = Policy(
        id=uuid.uuid4().hex[:10],
        title=title.strip()[:200],
        body=body.strip(),
        category=(category or "hr").lower()[:64],
        version=version[:32],
    )
    session.add(policy)
    await session.flush()
    n = 0
    for piece in chunk_text(body, size=380, overlap=50):
        session.add(
            PolicyChunk(
                id=uuid.uuid4().hex[:12],
                policy_id=policy.id,
                category=policy.category,
                text=piece,
            )
        )
        n += 1
    await session.commit()
    return {"policy_id": policy.id, "chunks": n}


async def list_policies(session: AsyncSession, category: str | None = None) -> list[Policy]:
    stmt = select(Policy)
    if category:
        stmt = stmt.where(Policy.category == category.lower())
    return list((await session.execute(stmt.order_by(Policy.created_at.desc()))).scalars())


async def ask(session: AsyncSession, question: str, category: str | None = None) -> dict:
    stmt = select(PolicyChunk)
    if category:
        stmt = stmt.where(PolicyChunk.category == category.lower())
    chunks = list((await session.execute(stmt)).scalars())
    policies = {p.id: p for p in (await session.execute(select(Policy))).scalars()}
    hits: list[Hit] = []
    for ch in chunks:
        s = score_chunk(question, ch.text)
        if s <= 0:
            continue
        pol = policies.get(ch.policy_id)
        title = pol.title if pol else ch.policy_id
        hits.append(
            Hit(
                chunk_id=ch.id,
                document_id=ch.policy_id,
                title=f"{title} ({ch.category})",
                text=ch.text,
                score=s,
                meta={"category": ch.category, "version": getattr(pol, "version", "")},
            )
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:5]
    context = pack_citations(hits) if hits else "(no policies match)"
    llm = get_llm()
    answer = await llm.complete(
        f"Internal policy assistant. Cite sources. If unknown, say escalate to HR/IT.\n"
        f"Q: {question}\n\nSOURCES:\n{context}",
        system="Never invent policy. Prefer short actionable answers.",
    )
    return {
        "answer": answer,
        "citations": [
            {
                "index": i,
                "policy_id": h.document_id,
                "title": h.title,
                "category": h.meta.get("category"),
                "score": round(h.score, 3),
                "snippet": h.text[:220],
            }
            for i, h in enumerate(hits, start=1)
        ],
    }
