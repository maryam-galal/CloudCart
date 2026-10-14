"""Lama's adapter for Rawan's existing SQLAlchemy models and SessionLocal.

This file creates no tables/engine and reads no credentials. Inject SessionLocal
from Rawan's database.py. Sessions are isolated per checkout/request.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timezone

from sqlalchemy import select, text, update

from .order_repository import ProductSnapshot
from .order_schemas import Order, OrderItem, Payment
from .order_service import CheckoutError


class SQLAlchemyOrderRepository:
    def __init__(self, session_factory, models_module=None):
        if models_module is None:
            from . import models as models_module
        self.session_factory = session_factory
        self.models = models_module
        self.active_session = ContextVar("orders_active_session", default=None)

    @staticmethod
    def _set_timezone(session):
        # TIMESTAMP values are interpreted as UTC in the API.
        if session.get_bind().dialect.name in {"mysql", "mariadb"}:
            session.execute(text("SET time_zone = '+00:00'"))

    @contextmanager
    def transaction(self):
        if self.active_session.get() is not None:
            raise RuntimeError("Nested checkout transactions are unsupported")
        with self.session_factory() as session:
            token = self.active_session.set(session)
            try:
                with session.begin():
                    self._set_timezone(session)
                    yield
            finally:
                self.active_session.reset(token)

    def _session(self):
        session = self.active_session.get()
        if session is None:
            raise RuntimeError("Checkout writes require an active transaction")
        return session

    def get_product_for_update(self, product_id):
        Product = self.models.Product
        statement = select(Product).where(
            Product.product_id == product_id
        ).with_for_update()
        product = self._session().scalar(statement)
        if product is None:
            return None
        return ProductSnapshot(product.product_id, product.name,
                               product.price, product.stock_quantity)

    def save_order(self, user_id, total, items):
        session = self._session()
        row = self.models.Order(user_id=user_id, total_amount=total, status="pending")
        session.add(row)
        session.flush()
        for item in items:
            session.add(self.models.OrderItem(
                order_id=row.order_id, product_id=item.product_id,
                quantity=item.quantity, unit_price=item.unit_price,
            ))
        session.flush()
        return self._to_order(session, row)

    def reduce_stock(self, product_id, quantity):
        Product = self.models.Product
        statement = update(Product).where(
            Product.product_id == product_id,
            Product.stock_quantity >= quantity,
        ).values(stock_quantity=Product.stock_quantity - quantity)
        result = self._session().execute(
            statement.execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise CheckoutError(400, "Product stock changed during checkout")

    def save_payment(self, order_id, payment_method, amount):
        row = self.models.Payment(order_id=order_id, payment_method=payment_method,
                                  amount=amount, status="pending")
        session = self._session()
        session.add(row)
        session.flush()
        return self._to_payment(row)

    @staticmethod
    def _to_payment(row):
        return Payment(id=row.payment_id, order_id=row.order_id,
                       payment_method=row.payment_method,
                       amount=row.amount, status=row.status)

    def _to_order(self, session, row):
        Item = self.models.OrderItem
        PaymentRow = self.models.Payment
        item_rows = session.scalars(select(Item).where(
            Item.order_id == row.order_id
        ).order_by(Item.order_item_id)).all()
        payment = session.scalar(select(PaymentRow).where(
            PaymentRow.order_id == row.order_id
        ))
        created = row.created_at
        created = (created.replace(tzinfo=timezone.utc) if created.tzinfo is None
                   else created.astimezone(timezone.utc))
        return Order(
            id=row.order_id, user_id=row.user_id, total_amount=row.total_amount,
            status=row.status, created_at=created,
            items=[OrderItem(id=item.order_item_id, order_id=item.order_id,
                             product_id=item.product_id, quantity=item.quantity,
                             unit_price=item.unit_price) for item in item_rows],
            payment=self._to_payment(payment) if payment is not None else None,
        )

    def list_orders(self, user_id):
        OrderRow = self.models.Order
        with self.session_factory() as session:
            self._set_timezone(session)
            rows = session.scalars(select(OrderRow).where(
                OrderRow.user_id == user_id
            ).order_by(OrderRow.order_id)).all()
            return [self._to_order(session, row) for row in rows]

    def get_order(self, order_id, user_id):
        OrderRow = self.models.Order
        with self.session_factory() as session:
            self._set_timezone(session)
            row = session.scalar(select(OrderRow).where(
                OrderRow.order_id == order_id, OrderRow.user_id == user_id,
            ))
            return self._to_order(session, row) if row is not None else None
