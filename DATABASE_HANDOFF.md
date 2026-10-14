# Orders database and authentication handoff

This is an interface proposal based on the supplied CloudCart plan. Confirm it with Rawan, Maryam and Basmala before treating it as the final shared contract. No changes to teammates' files are included in this package.

## Database fields required

| Table | Fields |
| --- | --- |
| products | id, name, price, stock_quantity |
| orders | id, user_id, total_amount, status, created_at |
| order_items | id, order_id, product_id, quantity, unit_price |
| payments | id, order_id (unique), payment_method, amount, status |
| users | id, as referenced by orders.user_id and returned by authentication |

Database is cloudcart on MySQL/RDS. Use DECIMAL(10,2) money columns and Python `Decimal`; agree currency together. The service rejects totals above 99999999.99. IDs follow the supplied BIGINT UNSIGNED AUTO_INCREMENT convention. The mock seeds use two decimal places. Database price/stock constraints and foreign keys must remain enforced. `pending` must be an allowed order status. Confirm whether an order reserves stock immediately; this module reduces stock at creation. The local runner additionally simulates payment statuses; actual cancellation/refund operations remain outside the production order endpoints.

These API data types are separate from Rawan's ORM models. The real adapter maps her rows/models to `ProductSnapshot`, `PricedItem`, `Order`, `OrderItem` and `Payment`. Confirm payment status spelling: the mock uses pending, paid, failed and refunded; methods are online and cash_on_delivery. The original items-only checkout remains accepted by defaulting its payment method to cash_on_delivery. Review this default and the added payment object in order responses with the team.

## Required adapter methods

| Method | Contract |
| --- | --- |
| transaction() | Context manager: start transaction; commit on successful exit; rollback on ANY error; close/release its connection/session |
| get_product_for_update(product_id) | Return ProductSnapshot or None; called within the active transaction; lock that product row until commit/rollback |
| save_order(user_id, total, items) | Insert order with pending status and all item rows; return Order with generated IDs and timestamp; do not commit here |
| save_payment(order_id, payment_method, amount) | Insert one pending payment, same calculated amount as order total; return Payment; unique order_id; use same transaction and do not commit here |
| reduce_stock(product_id, quantity) | Reduce stock using the same transaction; never allow negative stock; do not commit here |
| list_orders(user_id) | Return only this user's orders, including items and payment; ascending ID matches the mock |
| get_order(order_id, user_id) | Return that user's order with items and payment, or None for missing/other-user order |

For MySQL/InnoDB, use a transaction and indexed product lookup with `SELECT ... FOR UPDATE`, or an equivalent ORM locking read. The service locks products in ascending ID order. Save the order/items/payment and change stock on the **same connection/session**. Do not commit inside individual methods. Any commit/storage failure must propagate so the API cannot report a successful checkout prematurely.

The shared repository object must not hold one mutable global connection/session across all requests. Allocate a connection/session per checkout or request and isolate active transaction state by request/thread; a connection pool may supply them. Read methods also need properly scoped connections. The mock's global Python lock is only a simulation, not a substitute for MySQL row locks across multiple EC2 workers.

The current service uses synchronous methods. Rawan should supply a synchronous adapter, or the team must coordinate async changes rather than passing async methods into this interface.

Database errors, deadlock handling, maximum supported amounts/quantities and any retry/idempotency requirements should be decided with the team. The three assignment endpoints record pending payment methods but do not charge/refund money or implement idempotency keys: repeating a valid POST creates another order.

## Maryam's integration in the real app

Keep her existing FastAPI app and routers. Add the order router once:

```python
from app.orders import router as orders_router

app.include_router(orders_router, prefix="/api/orders")
```

This import assumes Maryam's existing project uses `app.*` imports and starts from `backend/`, as in the supplied plan. If she starts from the repository root, use `backend.app.*` consistently instead. Do not mix both import roots in one process because dependency override keys rely on function identity.

After Rawan provides the adapter, configure its instance in application startup:

```python
# The class and constructor are agreed with Rawan; no adapter exists yet.
app.state.order_repository = real_order_repository
```

In `order_dependencies.py`, replace the placeholder auth dependency with a wrapper around Maryam's verified user dependency:

```python
# Illustrative only: adapt the import/name and user.id to Maryam's real code.
from fastapi import Depends
from .auth import get_current_user

def get_current_user_id(user=Depends(get_current_user)) -> int:
    return user.id
```

Use the ID returned by verified authentication, never a client-supplied user ID. Real authentication must return 401 for missing/invalid credentials, and the authenticated user must exist in MySQL. Do not wire `get_demo_user_id` into the real app or deploy `demo_main.py`.

## Integration acceptance checks

1. Valid order persists with correct user_id and price snapshots.
2. Stock decreases by exactly the purchased quantities.
3. Invalid/missing/sold-out product causes no writes.
4. Forced failure after order/item/payment insertion or stock change rolls back order, items, payment and stock.
5. Two independent MySQL transactions cannot oversell the same product.
6. List and detail endpoints cannot expose another user's orders.
7. Order remains after restarting the application.
8. Real login identity replaces demo tokens.

All eight checks require the actual shared app/database. The mock test result does not certify them.

Payment status changes in production require verified provider events or authorized staff actions. Keep mock_payments.py routes out of the real app; register only the original order router. See PAYMENTS_LAMA.md for the local-only simulation contract.
