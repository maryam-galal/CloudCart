"""Local simulation routes. Never register these in Maryam's production app."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict

from .mock_order_repository import MockOrderRepository
from .order_dependencies import get_current_user_id, get_order_repository
from .order_schemas import Payment, PaymentStatus

router = APIRouter(tags=["Mock payment simulation"])


class MockPaymentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: PaymentStatus


@router.patch("/orders/{order_id}/payment", response_model=Payment,
              description="LOCAL MOCK ONLY: changes a status; no money is charged or refunded.")
def simulate_payment(
    order_id: Annotated[int, Path(gt=0)],
    payload: MockPaymentUpdate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    repository: Annotated[MockOrderRepository, Depends(get_order_repository)],
):
    if not isinstance(repository, MockOrderRepository):
        raise HTTPException(404, "Mock simulation is unavailable")
    try:
        payment = repository.simulate_payment_status(order_id, user_id, payload.status)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    if payment is None:
        raise HTTPException(404, "Order payment not found")
    return payment
