from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.demo_main import create_demo_app
from backend.app.mock_order_repository import MockOrderRepository
from backend.app.order_schemas import CheckoutRequest
from backend.app.order_service import CheckoutError, create_order
from backend.app.orders import router

HEADERS = {"Authorization": "Bearer mock-user-1"}
OTHER_USER = {"Authorization": "Bearer mock-user-2"}


@pytest.fixture
def setup():
    repository = MockOrderRepository()
    with TestClient(create_demo_app(repository)) as client:
        yield client, repository


def send(client, items):
    return client.post("/api/orders", headers=HEADERS, json={"items": items})


def test_checkout_total_stock_and_reads(setup):
    client, repository = setup
    response = send(client, [{"product_id": 1, "quantity": 2},
                             {"product_id": 2, "quantity": 1}])
    assert response.status_code == 201
    order = response.json()
    assert order["total_amount"] == "250.00"
    assert order["user_id"] == 1
    assert order["status"] == "pending"
    assert repository.products[1].stock_quantity == 3
    assert repository.products[2].stock_quantity == 9
    assert client.get("/api/orders", headers=HEADERS).json() == [order]
    assert client.get(f"/api/orders/{order['id']}", headers=HEADERS).json() == order


@pytest.mark.parametrize("items,code", [
    ([{"product_id": 999, "quantity": 1}], 404),
    ([{"product_id": 1, "quantity": 6}], 400),
    ([{"product_id": 3, "quantity": 1}], 400),
    ([{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 1}], 400),
    ([], 422),
    ([{"product_id": 1, "quantity": 0}], 422),
    ([{"product_id": 1, "quantity": -1}], 422),
    ([{"product_id": 1, "quantity": 1.5}], 422),
    ([{"product_id": 1, "quantity": True}], 422),
    ([{"product_id": "1", "quantity": 1}], 422),
    ([{"product_id": 1, "quantity": 1, "unit_price": 0.01}], 422),
    ([{"product_id": 1, "quantity": 1}, {"product_id": 3, "quantity": 1}], 400),
])
def test_invalid_order_changes_nothing(setup, items, code):
    client, repository = setup
    before = repository.products.copy()
    assert send(client, items).status_code == code
    assert repository.products == before
    assert repository.orders == {}


def test_body_cannot_choose_user_or_total(setup):
    client, _ = setup
    for extra in [{"user_id": 2}, {"total_amount": 0}]:
        response = client.post("/api/orders", headers=HEADERS,
                               json={"items": [{"product_id": 1, "quantity": 1}], **extra})
        assert response.status_code == 422


def test_unauthenticated_requests(setup):
    client, _ = setup
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/orders/1").status_code == 401
    assert client.post("/api/orders", json={"items": [{"product_id": 1, "quantity": 1}]}).status_code == 401
    assert client.get("/api/orders", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_user_cannot_read_someone_elses_orders(setup):
    client, _ = setup
    order = send(client, [{"product_id": 1, "quantity": 1}]).json()
    assert client.get("/api/orders", headers=OTHER_USER).json() == []
    assert client.get(f"/api/orders/{order['id']}", headers=OTHER_USER).status_code == 404
    assert client.get("/api/orders/999", headers=HEADERS).status_code == 404


def test_price_snapshot_survives_product_price_change(setup):
    client, repository = setup
    order = send(client, [{"product_id": 1, "quantity": 1}]).json()
    repository.products[1] = replace(repository.products[1], price=Decimal("999.00"))
    saved = client.get(f"/api/orders/{order['id']}", headers=HEADERS).json()
    assert saved["items"][0]["unit_price"] == "100.00"
    assert saved["total_amount"] == "100.00"


def test_storage_failure_rolls_back_everything():
    class FailingRepository(MockOrderRepository):
        def reduce_stock(self, product_id, quantity):
            super().reduce_stock(product_id, quantity)
            raise RuntimeError("simulated storage failure")

    repository = FailingRepository()
    with TestClient(create_demo_app(repository)) as client:
        response = send(client, [{"product_id": 1, "quantity": 1}])
    assert response.status_code == 500
    assert response.json() == {"detail": "Could not create order"}
    assert repository.orders == {}
    assert repository.products[1].stock_quantity == 5


def test_two_checkouts_cannot_buy_the_same_last_stock():
    repository = MockOrderRepository()
    request = CheckoutRequest(items=[{"product_id": 1, "quantity": 4}])

    def buy(user_id):
        try:
            create_order(request, user_id, repository)
            return 201
        except CheckoutError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(buy, [1, 2]))
    assert sorted(results) == [201, 400]
    assert repository.products[1].stock_quantity == 1
    assert len(repository.orders) == 1


def test_production_router_has_no_automatic_mock_login():
    application = FastAPI()
    application.include_router(router, prefix="/api/orders")
    with TestClient(application) as client:
        assert client.get("/api/orders", headers=HEADERS).status_code == 401


@pytest.mark.parametrize("method", ["cash_on_delivery", "online"])
def test_payment_method_and_server_calculated_amount(setup, method):
    client, repository = setup
    response = client.post("/api/orders", headers=HEADERS, json={
        "items": [{"product_id": 1, "quantity": 2}], "payment_method": method,
    })
    assert response.status_code == 201
    order = response.json()
    assert order["payment"] == {
        "id": 1, "order_id": order["id"], "payment_method": method,
        "amount": "200.00", "status": "pending",
    }
    assert len(repository.payments) == 1
    assert client.get(f"/api/orders/{order['id']}", headers=HEADERS).json() == order


def test_existing_requests_default_to_cash_on_delivery(setup):
    client, _ = setup
    response = send(client, [{"product_id": 2, "quantity": 1}])
    assert response.json()["payment"]["payment_method"] == "cash_on_delivery"


def test_invalid_payment_method_creates_nothing(setup):
    client, repository = setup
    response = client.post("/api/orders", headers=HEADERS, json={
        "items": [{"product_id": 1, "quantity": 1}], "payment_method": "invalid",
    })
    assert response.status_code == 422
    assert repository.orders == repository.payments == {}
    assert repository.products[1].stock_quantity == 5


def test_client_cannot_supply_payment_amount_or_success_status(setup):
    client, repository = setup
    response = client.post("/api/orders", headers=HEADERS, json={
        "items": [{"product_id": 1, "quantity": 1}],
        "payment_method": "online", "payment": {"amount": "0.01", "status": "paid"},
    })
    assert response.status_code == 422
    assert repository.orders == repository.payments == {}


def test_payment_failure_rolls_back_order_payment_and_stock():
    class FailingPaymentRepository(MockOrderRepository):
        def save_payment(self, order_id, payment_method, amount):
            super().save_payment(order_id, payment_method, amount)
            raise RuntimeError("simulated payment record failure")

    repository = FailingPaymentRepository()
    with TestClient(create_demo_app(repository)) as client:
        response = send(client, [{"product_id": 1, "quantity": 1}])
    assert response.status_code == 500
    assert repository.orders == repository.payments == {}
    assert repository.products[1].stock_quantity == 5
    assert repository.next_order_id == repository.next_payment_id == 1


def test_total_fits_shared_decimal_column(setup):
    client, repository = setup
    repository.products[1] = replace(repository.products[1], stock_quantity=1000000)
    response = send(client, [{"product_id": 1, "quantity": 1000000}])
    assert response.status_code == 400
    assert repository.orders == repository.payments == {}
    assert repository.products[1].stock_quantity == 1000000


def test_mock_paid_and_refunded_lifecycle(setup):
    client, repository = setup
    order = send(client, [{"product_id": 1, "quantity": 1}]).json()
    path = f"/mock/orders/{order['id']}/payment"
    for status in ["paid", "refunded", "refunded"]:
        response = client.patch(path, headers=HEADERS, json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status
        assert response.json()["amount"] == "100.00"
    assert client.get(f"/api/orders/{order['id']}", headers=HEADERS).json()["payment"]["status"] == "refunded"
    assert repository.products[1].stock_quantity == 4  # Status simulation does not restock.
    assert len(repository.payments) == 1
    assert client.patch(path, headers=HEADERS, json={"status": "paid"}).status_code == 409


def test_mock_failed_payment_can_be_retried(setup):
    client, _ = setup
    order = send(client, [{"product_id": 1, "quantity": 1}]).json()
    path = f"/mock/orders/{order['id']}/payment"
    for status in ["failed", "pending", "paid"]:
        response = client.patch(path, headers=HEADERS, json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status


@pytest.mark.parametrize("target", ["refunded", "invalid"])
def test_invalid_mock_payment_transition_preserves_state(setup, target):
    client, repository = setup
    order = send(client, [{"product_id": 1, "quantity": 1}]).json()
    response = client.patch(f"/mock/orders/{order['id']}/payment", headers=HEADERS,
                            json={"status": target})
    assert response.status_code == (409 if target == "refunded" else 422)
    assert repository.payments[order['id']].status == "pending"


def test_mock_payment_status_requires_ownership_and_auth(setup):
    client, repository = setup
    order = send(client, [{"product_id": 1, "quantity": 1}]).json()
    path = f"/mock/orders/{order['id']}/payment"
    assert client.patch(path, headers=OTHER_USER, json={"status": "paid"}).status_code == 404
    assert client.patch(path, json={"status": "paid"}).status_code == 401
    assert client.patch("/mock/orders/999/payment", headers=HEADERS, json={"status": "paid"}).status_code == 404
    assert repository.payments[order['id']].status == "pending"


def test_mock_payment_route_is_not_in_production_order_router():
    application = FastAPI()
    application.include_router(router, prefix="/api/orders")
    assert not any(path.startswith("/mock") for path in application.openapi()["paths"])
