"""Local in-memory database: one process, reset on restart; never deploy it."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock

from .order_repository import PricedItem, ProductSnapshot
from .order_schemas import Order, OrderItem, Payment


class MockOrderRepository:
    def __init__(self):
        self.products = {
            1: ProductSnapshot(1, "Keyboard", Decimal("100.00"), 5),
            2: ProductSnapshot(2, "Mouse", Decimal("50.00"), 10),
            3: ProductSnapshot(3, "Headphones", Decimal("200.00"), 0),
        }
        self.orders: dict[int, Order] = {}
        self.payments: dict[int, Payment] = {}  # Keyed by unique order_id.
        self.next_order_id = 1
        self.next_item_id = 1
        self.next_payment_id = 1
        self.lock = RLock()

    @contextmanager
    def transaction(self):
        # Hold the lock across the entire checkout, not just each method.
        with self.lock:
            previous = (self.products.copy(), self.orders.copy(), self.payments.copy(),
                        self.next_order_id, self.next_item_id, self.next_payment_id)
            try:
                yield
            except BaseException:
                (self.products, self.orders, self.payments,
                 self.next_order_id, self.next_item_id, self.next_payment_id) = previous
                raise

    def get_product_for_update(self, product_id):
        # Called only inside transaction(). Products are immutable snapshots.
        return self.products.get(product_id)

    def reduce_stock(self, product_id, quantity):
        product = self.products[product_id]
        if quantity > product.stock_quantity:
            raise RuntimeError("Stock changed during checkout")
        self.products[product_id] = replace(
            product, stock_quantity=product.stock_quantity - quantity
        )

    def save_order(self, user_id: int, total: Decimal, items: list[PricedItem]):
        order_id = self.next_order_id
        saved_items = []
        for item in items:
            saved_items.append(OrderItem(
                id=self.next_item_id, order_id=order_id,
                product_id=item.product_id, quantity=item.quantity,
                unit_price=item.unit_price,
            ))
            self.next_item_id += 1
        order = Order(id=order_id, user_id=user_id, total_amount=total,
                      status="pending", created_at=datetime.now(timezone.utc),
                      items=saved_items)
        self.orders[order_id] = order
        self.next_order_id += 1
        return order.model_copy(deep=True)

    def save_payment(self, order_id, payment_method, amount):
        if order_id in self.payments:
            raise RuntimeError("An order can have only one payment record")
        payment = Payment(id=self.next_payment_id, order_id=order_id,
                          payment_method=payment_method, amount=amount)
        self.payments[order_id] = payment
        self.next_payment_id += 1
        # Replace rather than mutate, preserving transaction rollback snapshots.
        order = self.orders[order_id].model_copy(deep=True)
        order.payment = payment.model_copy(deep=True)
        self.orders[order_id] = order
        return payment.model_copy(deep=True)

    def simulate_payment_status(self, order_id, user_id, status):
        """Mock only. Real payment updates need verified provider/admin events."""
        with self.lock:
            order = self.orders.get(order_id)
            if order is None or order.user_id != user_id:
                return None
            payment = self.payments.get(order_id)
            if payment is None:
                return None
            allowed = {"pending": {"paid", "failed"}, "failed": {"pending"},
                       "paid": {"refunded"}, "refunded": set()}
            if status != payment.status and status not in allowed[payment.status]:
                raise ValueError(f"Cannot change payment from {payment.status} to {status}")
            updated = payment.model_copy(update={"status": status}, deep=True)
            updated_order = order.model_copy(deep=True)
            updated_order.payment = updated.model_copy(deep=True)
            self.payments[order_id] = updated
            self.orders[order_id] = updated_order
            return updated.model_copy(deep=True)

    def list_orders(self, user_id):
        with self.lock:
            return [order.model_copy(deep=True) for order in self.orders.values()
                    if order.user_id == user_id]

    def get_order(self, order_id, user_id):
        with self.lock:
            order = self.orders.get(order_id)
            if order is None or order.user_id != user_id:
                return None
            return order.model_copy(deep=True)
