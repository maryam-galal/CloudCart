"""Checkout rules: reused unchanged with either database implementation."""
from decimal import Decimal

from .order_repository import OrderRepository, PricedItem
from .order_schemas import CheckoutRequest, Order

MAX_AMOUNT = Decimal("99999999.99")  # Shared schema: DECIMAL(10,2).


class CheckoutError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def create_order(request: CheckoutRequest, user_id: int,
                 repository: OrderRepository) -> Order:
    ids = [item.product_id for item in request.items]
    if len(ids) != len(set(ids)):
        raise CheckoutError(400, "Each product must appear only once")

    # Sorted locking order reduces deadlock risk in the real database.
    with repository.transaction():
        priced_items = []
        total = Decimal("0.00")
        for item in sorted(request.items, key=lambda row: row.product_id):
            product = repository.get_product_for_update(item.product_id)
            if product is None:
                raise CheckoutError(404, f"Product {item.product_id} not found")
            if product.stock_quantity < item.quantity:
                raise CheckoutError(400, f"Not enough stock for product {item.product_id}")
            if (not product.price.is_finite() or product.price < 0
                    or product.price > MAX_AMOUNT
                    or product.price != product.price.quantize(Decimal("0.01"))):
                raise RuntimeError("Invalid stored product price")
            priced_items.append(PricedItem(item.product_id, item.quantity, product.price))
            total += product.price * item.quantity

        if total > MAX_AMOUNT:
            raise CheckoutError(400, "Order total exceeds the supported amount")

        order = repository.save_order(user_id, total, priced_items)
        for item in priced_items:
            repository.reduce_stock(item.product_id, item.quantity)
        # Recording a pending payment is not charging a customer.
        order.payment = repository.save_payment(order.id, request.payment_method, total)

    # Return only after the transaction has committed successfully.
    return order
