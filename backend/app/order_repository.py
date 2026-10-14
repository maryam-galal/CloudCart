"""The interface Rawan's real database adapter must implement."""
from contextlib import AbstractContextManager
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .order_schemas import Order, Payment


@dataclass(frozen=True)
class ProductSnapshot:
    id: int
    name: str
    price: Decimal
    stock_quantity: int


@dataclass(frozen=True)
class PricedItem:
    product_id: int
    quantity: int
    unit_price: Decimal


class OrderRepository(Protocol):
    def transaction(self) -> AbstractContextManager[None]: ...
    def get_product_for_update(self, product_id: int) -> ProductSnapshot | None: ...
    def reduce_stock(self, product_id: int, quantity: int) -> None: ...
    def save_order(self, user_id: int, total: Decimal, items: list[PricedItem]) -> Order: ...
    def save_payment(self, order_id: int, payment_method: str, amount: Decimal) -> Payment: ...
    def list_orders(self, user_id: int) -> list[Order]: ...
    def get_order(self, order_id: int, user_id: int) -> Order | None: ...
