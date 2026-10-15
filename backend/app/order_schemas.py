"""API data shapes, separate from Rawan's database/ORM models."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

PositiveInteger = Annotated[int, Field(strict=True, gt=0)]
PaymentStatus = Literal["pending", "paid", "failed", "refunded"]


class CheckoutItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: PositiveInteger
    quantity: PositiveInteger


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CheckoutItem] = Field(min_length=1, max_length=100)
    payment_method: Literal["online", "cash_on_delivery"] = "cash_on_delivery"


class OrderItem(BaseModel):
    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal


class Payment(BaseModel):
    id: int
    order_id: int
    payment_method: Literal["online", "cash_on_delivery"]
    amount: Decimal
    status: PaymentStatus = "pending"


class Order(BaseModel):
    id: int
    user_id: int
    total_amount: Decimal
    status: str
    created_at: datetime
    items: list[OrderItem]
    payment: Payment | None = None
