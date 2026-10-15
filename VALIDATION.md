# Validation result

Prepared on 2026-10-13 using Python 3.12.

Command from project root: `python -m pytest -q`

Result: **33 passed** with payment method and status support.

All tests used isolated in-memory databases. Tests verify order totals, stock changes, input validation, user isolation, missing orders/products, price snapshots, rollback after an injected write failure, and concurrent checkout stock protection in one process. The production router has no automatic demo authentication.

New tests cover both payment methods, server-calculated payment amounts, invalid payment method, spoofed payment details, rollback after a payment record failure, the DECIMAL(10,2) amount limit, paid/refunded/failed/retry transitions, ownership checks and exclusion of simulation routes from the production orders router. One deprecation warning was reported by Starlette/AnyIO; tests passed.

Starlette is pinned to 0.50.0 so the dependency metadata supports Python 3.10.5. All installed dependencies were checked against that Python version; execution tests here used Python 3.12. Installed versions are recorded in requirements-lama.txt. Coordinate any dependency changes with the shared project.

No live MySQL/RDS connection, real login, AWS deployment, GitHub push or cross-process database concurrency was tested. Those checks remain for integration.

Additional verification: started a local Uvicorn server, checked /health and /docs, and sent all 19 Postman collection requests over HTTP. Their expected status codes passed, and the first valid order total was 250.00. The OpenAPI schema includes all three order operations, the local simulation route and Bearer authorization. No actual money was charged or refunded.
