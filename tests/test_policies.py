import pytest

@pytest.mark.asyncio
async def test_publish_and_ask(client):
    r = await client.post(
        "/api/policies",
        json={
            "title": "PTO Policy",
            "category": "hr",
            "body": "Full-time employees receive 20 days of paid time off per calendar year. "
            "Requests must be submitted in the HR portal at least 5 business days ahead.",
        },
    )
    assert r.status_code == 200
    ask = await client.post(
        "/api/ask", json={"question": "How many PTO days do I get?", "category": "hr"}
    )
    assert ask.status_code == 200
    assert ask.json()["citations"]
