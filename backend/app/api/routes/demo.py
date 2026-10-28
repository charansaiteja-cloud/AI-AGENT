from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.serializers import customer_out
from backend.app.db.database import get_db
from backend.app.models.customer import Customer
from backend.app.schemas.customer import CustomerOut

router = APIRouter(tags=["demo"])

DEMO_EMAIL = "sarah@acme.example"
DEMO_NAME = "Sarah Chen"
DEMO_FIRST_MESSAGE = (
    "My name is Sarah. I work at Acme Corp. I'm using Ubuntu 24.04 on a "
    "Dell XPS 15. My Wi-Fi keeps disconnecting."
)
DEMO_FOLLOW_UP = "The Wi-Fi problem is back."


@router.post("/demo/seed", response_model=CustomerOut)
async def seed_demo_customer(
    db: AsyncSession = Depends(get_db),
) -> CustomerOut:
    customer = await db.scalar(select(Customer).where(func.lower(Customer.email) == DEMO_EMAIL))

    if customer is None:
        customer = Customer(name=DEMO_NAME, email=DEMO_EMAIL)
        db.add(customer)
        await db.commit()
        await db.refresh(customer)

    return customer_out(customer)


@router.get("/demo/scenario")
async def demo_scenario() -> dict[str, object]:
    return {
        "customer": {"name": DEMO_NAME, "email": DEMO_EMAIL},
        "first_message": DEMO_FIRST_MESSAGE,
        "follow_up": DEMO_FOLLOW_UP,
        "steps": [
            "Load the demo customer.",
            "Send the first message in a new conversation.",
            "Wait for the 'Memory saved' indicator.",
            "Start another conversation and send the follow-up.",
            "Inspect the recalled memories in the memory panel.",
        ],
    }
