"""Real app/auth/SQLAlchemy wiring on isolated SQLite, never the live RDS DB.

SQLite verifies application behavior and rollback. MySQL row locking and
cross-worker concurrency still require acceptance tests on the real database.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app import auth, models, orders_auth
from app.database import get_db
from app.database_orders import SQLAlchemyOrderRepository
from app.main import app

TEST_SECRET = "isolated-tests-only-secret-with-at-least-32-characters"
TEST_PASSWORD = "TestPassword123!"
PASSWORD_HASH = PasswordHash.recommended().hash(TEST_PASSWORD)


@compiles(BIGINT, "sqlite")
def compile_test_bigint(type_, compiler, **kwargs):
    # SQLite autoincrement requires the exact INTEGER type name.
    return "INTEGER"


@pytest.fixture
def real_app(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "orders.sqlite"),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    models.Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as db:
        db.add_all([
            models.User(user_id=1, name="First User", email="first@example.com",
                        password_hash=PASSWORD_HASH),
            models.User(user_id=2, name="Second User", email="second@example.com",
                        password_hash=PASSWORD_HASH),
            models.Product(product_id=1, name="Keyboard", price=Decimal("100.00"),
                           stock_quantity=5),
            models.Product(product_id=2, name="Mouse", price=Decimal("50.00"),
                           stock_quantity=10),
            models.Product(product_id=3, name="Headphones", price=Decimal("200.00"),
                           stock_quantity=0),
        ])

    def test_database():
        with sessions() as db:
            yield db

    monkeypatch.setattr(orders_auth, "JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setattr(auth, "JWT_SECRET_KEY", TEST_SECRET)
    repository = SQLAlchemyOrderRepository(sessions)
    monkeypatch.setattr(app.state, "order_repository", repository)
    app.dependency_overrides[get_db] = test_database
    try:
        with TestClient(app) as client:
            yield client, sessions, repository
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def signed_token(subject="1", *, key=TEST_SECRET, algorithm="HS256", **extra):
    claims = {"sub": subject,
              "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}
    claims.update(extra)
    return jwt.encode(claims, key, algorithm=algorithm)


def headers(subject="1"):
    return {"Authorization": "Bearer " + signed_token(subject)}


def test_signup_login_and_order_with_real_dependencies(real_app):
    client, sessions, _ = real_app
    signup = client.post("/api/auth/signup", json={
        "name": "New Customer", "email": "new@example.com",
        "password": TEST_PASSWORD,
    })
    assert signup.status_code == 201
    owner = signup.json()["user"]["user_id"]
    login = client.post("/api/auth/login", json={
        "email": "new@example.com", "password": TEST_PASSWORD,
    })
    assert login.status_code == 200
    authorization = {"Authorization": "Bearer " + login.json()["access_token"]}
    response = client.post("/api/orders", headers=authorization, json={
        "items": [{"product_id": 1, "quantity": 2},
                  {"product_id": 2, "quantity": 1}],
        "payment_method": "cash_on_delivery",
    })
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["user_id"] == owner
    assert order["total_amount"] == "250.00"
    assert order["payment"]["status"] == "pending"
    assert len(order["items"]) == 2
    assert client.get("/api/orders", headers=authorization).json() == [order]
    assert client.get(f"/api/orders/{order['id']}", headers=authorization).json() == order
    with sessions() as db:
        assert db.get(models.Product, 1).stock_quantity == 3
        assert db.get(models.Product, 2).stock_quantity == 9
        assert db.get(models.Order, order["id"]).user_id == owner
        assert db.scalar(select(func.count()).select_from(models.Payment)) == 1


@pytest.mark.parametrize("token", [
    "mock-user-1", "not-a-jwt", signed_token("999"),
    signed_token("0"), signed_token("-1"), signed_token("user-123"),
    signed_token("18446744073709551616"), signed_token("1" * 100),
    signed_token("١"), signed_token(1),
    signed_token(key="different-signing-key-with-at-least-32-characters"),
    signed_token(algorithm="HS384"),
    signed_token(exp=datetime.now(timezone.utc) - timedelta(minutes=1)),
    jwt.encode({"sub": "1"}, TEST_SECRET, algorithm="HS256"),
    jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
               TEST_SECRET, algorithm="HS256"),
])
def test_real_orders_reject_invalid_expired_and_unknown_users(real_app, token):
    client, _, _ = real_app
    response = client.get("/api/orders", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_missing_authentication_is_rejected(real_app):
    client, _, _ = real_app
    assert client.get("/api/orders").status_code == 401


def test_missing_secret_does_not_accept_requests(real_app, monkeypatch):
    client, _, _ = real_app
    monkeypatch.setattr(orders_auth, "JWT_SECRET_KEY", "")
    assert client.get("/api/orders", headers=headers()).status_code == 503


def test_other_customer_cannot_read_order(real_app):
    client, _, _ = real_app
    response = client.post("/api/orders", headers=headers(), json={
        "items": [{"product_id": 1, "quantity": 1}],
    })
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert client.get("/api/orders", headers=headers("2")).json() == []
    assert client.get(f"/api/orders/{order_id}", headers=headers("2")).status_code == 404


@pytest.mark.parametrize("product_id,quantity,status", [(3, 1, 400), (999, 1, 404), (1, 6, 400)])
def test_rejected_checkout_leaves_real_tables_unchanged(real_app, product_id, quantity, status):
    client, sessions, _ = real_app
    response = client.post("/api/orders", headers=headers(), json={
        "items": [{"product_id": product_id, "quantity": quantity}],
    })
    assert response.status_code == status
    with sessions() as db:
        for model in (models.Order, models.OrderItem, models.Payment):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert db.get(models.Product, 1).stock_quantity == 5


def test_payment_failure_rolls_back_sqlalchemy_order_items_and_stock(real_app, monkeypatch):
    client, sessions, repository = real_app

    def fail_payment(*args):
        raise RuntimeError("injected payment-storage failure")

    monkeypatch.setattr(repository, "save_payment", fail_payment)
    response = client.post("/api/orders", headers=headers(), json={
        "items": [{"product_id": 1, "quantity": 2}],
    })
    assert response.status_code == 500
    with sessions() as db:
        for model in (models.Order, models.OrderItem, models.Payment):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert db.get(models.Product, 1).stock_quantity == 5


def test_shared_app_has_order_routes_without_payment_simulation(real_app):
    client, _, _ = real_app
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/orders" in paths
    assert "/api/orders/{order_id}" in paths
    assert not any(path.startswith("/mock") for path in paths)
