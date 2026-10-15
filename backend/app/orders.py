import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from .order_dependencies import get_current_user_id, get_order_repository
from .order_repository import OrderRepository
from .order_schemas import CheckoutRequest, Order
from .order_service import CheckoutError, create_order

router = APIRouter(tags=["Orders"])
logger = logging.getLogger(__name__)
Repository = Annotated[OrderRepository, Depends(get_order_repository)]
CurrentUser = Annotated[int, Depends(get_current_user_id)]


@router.post("", response_model=Order, status_code=201)
def checkout(payload: CheckoutRequest, user_id: CurrentUser, repository: Repository):
    try:
        order = create_order(payload, user_id, repository)
    except CheckoutError as error:
        logger.info("checkout_rejected status=%s", error.status_code)
        raise HTTPException(error.status_code, error.detail) from error
    except Exception as error:
        # Log the type, not database error text that could contain credentials.
        logger.error("checkout_failed error_type=%s", type(error).__name__)
        raise HTTPException(500, "Could not create order") from error
    logger.info("order_created order_id=%s user_id=%s", order.id, user_id)
    return order


@router.get("", response_model=list[Order])
def list_my_orders(user_id: CurrentUser, repository: Repository):
    return repository.list_orders(user_id)


@router.get("/{order_id}", response_model=Order)
def get_my_order(order_id: Annotated[int, Path(gt=0)], user_id: CurrentUser,
                 repository: Repository):
    order = repository.get_order(order_id, user_id)
    if order is None:
        raise HTTPException(404, "Order not found")
    return order
