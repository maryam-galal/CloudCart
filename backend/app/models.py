from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Integer,
    String,
    Text,
    Numeric,
    TIMESTAMP,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'customer'")
    )


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint(
            "stock_quantity >= 0",
            name="ck_products_stock_nonnegative",
        ),
    )

    product_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
  
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    image_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0", name="ck_orders_total_nonnegative"
        ),
    )

    order_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("users.user_id"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint(
            "unit_price >= 0", name="ck_order_items_price_nonnegative"
        ),
    )

    order_item_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    order_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("products.product_id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonnegative"),
    )

    payment_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )
    order_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("orders.order_id"),
        unique=True,
        nullable=False,
    )
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
