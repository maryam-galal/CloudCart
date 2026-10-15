# Lama's mock payment methods and statuses

This update adds a payment record to order checkout using the `payments` fields in your team's screenshot. It does not connect to a bank or payment provider. All status changes here are simulations.

## Method, payment status and order status

| Field | Values in this module | Meaning |
| --- | --- | --- |
| payment_method | cash_on_delivery, online | How the customer intends to pay |
| payment.status | pending, paid, failed, refunded | State of the payment |
| order.status | pending on creation | Separate state of the order |

`paid` represents "payment done". Refund is a payment status, not a method. Your screenshot specifies a status column but not its enum values; confirm these spellings against Rawan's actual SQL before integration.

بالمصري: طريقة الدفع كاش عند الاستلام أو أونلاين. حالة الدفع لسه مستني، اتدفع، فشل، أو اترد. حالة الأوردر نفسها حاجة منفصلة.

Every new order creates one pending payment record with `amount` equal to the server-calculated `total_amount`. This is one payment per order, matching the unique `payments.order_id` contract. The client cannot supply its own price, total, payment amount or payment status during checkout.

For compatibility with the original `items`-only API contract, missing `payment_method` defaults to `cash_on_delivery`. Tell Maryam and Rawan about this proposed default and the added response `payment` object before merging. Both explicit methods are accepted. The total is the sum of item prices × quantities; no taxes, shipping fees or discounts have been specified.

## Apply this update to your existing local folder

1. Stop your local server with Ctrl+C in its terminal.
2. Extract the updated ZIP into a separate temporary folder.
3. Copy these files into matching paths in your existing project, replacing the earlier copies:
   - backend/app/order_schemas.py
   - backend/app/order_repository.py
   - backend/app/order_service.py
   - backend/app/mock_order_repository.py
   - backend/app/demo_main.py
   - backend/app/mock_payments.py (new)
   - tests/test_orders.py
4. Copy the updated Postman collection and guides too, for GitHub handoff.
5. Keep your existing .venv. Dependencies are unchanged; requirements-lama.txt still uses starlette==0.50.0.
6. From your project root, run ` .\.venv\Scripts\python.exe -m pytest tests/test_orders.py -q `; expect 33 passed.
7. Restart with ` .\.venv\Scripts\python.exe -m uvicorn backend.app.demo_main:app --reload `.

This restart resets the mock database, so your first new order will be ID 1.

## Create an order with a method

At http://127.0.0.1:8000/docs, Authorize with `mock-user-1`. POST /api/orders:

```json
{
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 2, "quantity": 1}
  ],
  "payment_method": "cash_on_delivery"
}
```

Expect 201, `total_amount: "250.00"`, and:

```json
{
  "id": 1,
  "order_id": 1,
  "payment_method": "cash_on_delivery",
  "amount": "250.00",
  "status": "pending"
}
```

This object appears under `payment` in the order response. Repeat with `payment_method: "online"` to test the other method; that is a separate order, and its payment also starts pending. No card details are requested and no money is moved.

## Simulate payment done and refunded

The LOCAL demo has an extra route: PATCH `/mock/orders/{order_id}/payment`. This route belongs only to `demo_main.py`, not the production `orders.py` router.

1. Use order_id 1 and body `{"status":"paid"}`. Expect 200 and payment status paid.
2. GET /api/orders/1. Its `payment.status` should now be paid.
3. PATCH the same mock route with `{"status":"refunded"}`. Expect 200 and refunded.
4. GET /api/orders/1 again. The payment method and original amount stay recorded; its status is refunded.
5. Try marking this refunded payment paid again. Expect 409.

Allowed changes are pending → paid or failed; failed → pending for a retry; paid → refunded. Repeating the current status returns the same result. Refunded is terminal. Another user cannot simulate changes to your payment; missing authentication returns 401.

These updates only simulate payment tracking. They do not charge/refund money, cancel an order, change order.status or restock products. Actual refunds, settlement, cancellations and restocking policies need the team/provider workflow. The given one-record schema does not track partial refund amounts or multiple payment attempts as separate history records.

## Real integration

Rawan implements `save_payment(order_id, payment_method, amount)` on the real repository, in the same transaction as order/items/stock. Order reads must include the associated payment. A failed payment INSERT must roll back the entire checkout.

Never register `/mock` routes in the deployed shared application. Real paid/refunded statuses must come from verified payment-provider events or authorized cash-collection/refund actions. This package does not implement those production workflows.

Your GitHub branch remains `feature/orders-checkout`. Commit only your module, tests and related guides. Coordinate these added fields with Maryam/Rawan; do not change their auth, models or connection code independently.
