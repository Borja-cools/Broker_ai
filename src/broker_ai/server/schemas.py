"""Gevalideerde JSON-contracten voor de versie 1 API."""

from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)]


class ApprovalMode(str, Enum):
    MANUAL = "manual"
    AUTOMATIC_LIMITED = "automatic_limited"
    DISABLED = "disabled"


class BotStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"


class BotCreate(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=80)]
    specialization: Annotated[str, Field(min_length=2, max_length=160)]
    approval_mode: ApprovalMode = ApprovalMode.MANUAL
    max_auto_order_value: PositiveMoney = Decimal("50")


class ProposalCreate(BaseModel):
    bot_id: str
    symbol: Annotated[str, Field(pattern=r"^[A-Za-z0-9]{1,15}$")]
    side: Annotated[str, Field(pattern=r"^(buy|sell)$")]
    quantity: PositiveMoney
    price: PositiveMoney
    rationale: Annotated[str, Field(min_length=5, max_length=1000)]


class DecisionCreate(BaseModel):
    decision: Annotated[str, Field(pattern=r"^(approve|reject)$")]
