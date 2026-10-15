# Lama's CloudCart orders module — start here

Your work is ready to run locally with a mock database. It follows the attached CloudCart plan and provides these three endpoints:

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/api/orders` | Checks stock, calculates prices, saves an order and reduces stock |
| GET | `/api/orders` | Lists only the current user's orders |
| GET | `/api/orders/{order_id}` | Returns one order belonging to the current user |

**Mock database** means temporary sample data held in Python memory. You do not need MySQL, RDS or AWS for these steps. Restarting the server resets products and removes orders. Use one local server process.

بالمصري: الـ mock database بيانات تجريبية جوّه بايثون. هتقدري تخلصي وتختبري جزء الأوردرات دلوقتي. أول ما السيرفر يتعمله restart، البيانات بترجع للبداية.

Checkout now records a payment method and one pending payment per order. See PAYMENTS_LAMA.md for cash_on_delivery, online and local status simulations. This is payment tracking, not a payment gateway; no money is charged or refunded.

## 1. Open the project in VS Code

1. Extract `CloudCart-Lama.zip`.
2. Open VS Code → File → Open Folder.
3. Select the extracted **CloudCart-Lama** folder containing this guide and `requirements-lama.txt`.
4. Open Terminal → New Terminal. The commands below use Windows PowerShell.

You can test this downloaded project first, then copy your files into Maryam's shared repository in Step 9. You do not need to create another GitHub repository.

## 2. Create your Python environment

Use Python 3.10 or newer. Your Python 3.10.5 can use these dependency versions; the package was tested here on Python 3.12.

Run these commands one at a time:

```powershell
py -3.10 --version
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lama.txt
```

The virtual environment is a separate place for this project's packages. These commands call its Python directly, so you do not need to activate it or change PowerShell execution policy.

بالمصري: بنعمل بيئة منفصلة للمشروع، وبننزل فيها المكتبات اللي محتاجينها بس.

On macOS/Linux, use `python3.10 -m venv .venv`, then `.venv/bin/python` instead of `.\.venv\Scripts\python.exe` in every command.

## 3. Understand the files you own

You do not need to type the code again; it is included in this project.

| File in `backend/app/` | Purpose |
| --- | --- |
| `orders.py` | Your three API endpoints |
| `order_schemas.py` | Required request fields and response formats; these are API schemas, not Rawan's ORM models |
| `order_service.py` | Stock checks, server-side price calculation and checkout rules |
| `order_repository.py` | The agreed interface for mock and real database access |
| `mock_order_repository.py` | Temporary products, orders and transaction simulation |
| `order_dependencies.py` | Database and authentication integration points |
| `demo_main.py` | Your local runner, separate from Maryam's `main.py` |
| `mock_payments.py` | Local paid/failed/refunded simulations; never register in the real app |

`tests/test_orders.py` contains the checkout tests. `postman/Lama_Orders.postman_collection.json` contains ready-made manual requests.

A **repository** here means the Python object that reads/writes data. It is different from a GitHub repository. An **adapter** is the implementation that translates these methods into Rawan's database queries.

بالمصري: الـ service فيه قواعد الأوردر. الـ repository هو الجزء اللي بيقرأ ويكتب البيانات. بعدين هنبدّل طريقة القراءة والكتابة، وقواعد الأوردر تفضل زي ما هي.

## 4. Start the local API

From the project folder, run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.demo_main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal running. Open:

- Health: http://127.0.0.1:8000/health — expect `{"status":"ok","mode":"local-mock"}`.
- Interactive API: http://127.0.0.1:8000/docs.

If port 8000 is busy, stop your other local server or choose another port and update the Postman `base_url` variable.

## 5. Use the local demo user

In `/docs`, click **Authorize**. Enter **mock-user-1** as the token value; do not type the word Bearer in that box. Click Authorize, then Close.

This means user 1 for local tests. `mock-user-2` means user 2. These are fixed demo tokens, not real login tokens. They exist only in `demo_main.py`; the actual router refuses access until Maryam wires real authentication.

بالمصري: بنستخدم يوزر وهمي علشان نختبر. بعدين Maryam هتوصّل اليوزر الحقيقي من الـ login. الفرونت إند مش هيبعت `user_id` جوّه الأوردر.

Sample products:

| Product ID | Name | Price | Starting stock |
| --- | --- | --- | --- |
| 1 | Keyboard | 100.00 | 5 |
| 2 | Mouse | 50.00 | 10 |
| 3 | Headphones | 200.00 | 0 |

Prices are example values; agree the currency with the team. Money uses `Decimal` rather than binary floating point, and JSON responses show amounts as strings such as `"250.00"`.

## 6. Create and retrieve an order

In `/docs`, expand **POST /api/orders** → Try it out. Replace the request body with:

```json
{
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 2, "quantity": 1}
  ]
}
```

Click Execute. Expect HTTP **201** and:

- `id`: 1 on a fresh server.
- `user_id`: 1.
- `total_amount`: `"250.00"` because 2 × 100 + 1 × 50 = 250.
- `status`: `"pending"`.
- `items`: purchased quantities and the prices at checkout.

The remaining stock becomes 3 keyboards and 9 mice. Do not send prices, `user_id` or total in the request. Extra fields are rejected.

Now execute **GET /api/orders**. Expect **200** and a list containing the order.

Execute **GET /api/orders/{order_id}** using the ID returned by POST. Expect **200** and that order.

بالمصري: العميل بيبعت رقم المنتج والكمية بس. السيرفر هو اللي يجيب السعر ويحسب الإجمالي ويقلّل المخزون.

## 7. Test failures and user isolation

Use the following requests separately. If you repeat successful checkouts, stock will decrease; restart the server for a fresh starting state.

| Case | Body or action | Expected |
| --- | --- | --- |
| More than available stock | `{"items":[{"product_id":1,"quantity":99}]}` | 400 |
| Sold out | `{"items":[{"product_id":3,"quantity":1}]}` | 400 |
| Unknown product | `{"items":[{"product_id":999,"quantity":1}]}` | 404 |
| Zero quantity | `{"items":[{"product_id":1,"quantity":0}]}` | 422 |
| Negative quantity | `{"items":[{"product_id":1,"quantity":-1}]}` | 422 |
| Empty checkout | `{"items":[]}` | 422 |
| Duplicate product | `{"items":[{"product_id":1,"quantity":1},{"product_id":1,"quantity":1}]}` | 400 |
| Client tries setting a price | `{"items":[{"product_id":1,"quantity":1,"unit_price":0.01}]}` | 422 |
| No token | Remove authorization and call GET /api/orders | 401 |
| Another user's orders | Switch to mock-user-2; call GET /api/orders | 200 with an empty list |
| Another user's order | As mock-user-2, GET the order ID created by user 1 | 404 |

A rejected checkout must not save an order or reduce stock. A **transaction** means saving the order, saving its items and reducing stock succeed together; if a step fails, they are all undone.

بالمصري: العملية يا إمّا تتم كلها، يا إمّا ما يحصلش منها أي تغيير. مينفعش المخزون يقل والأوردر ما يتسجلش.

For Postman: Import → select `postman/Lama_Orders.postman_collection.json`. Its collection variables already contain the local URL and demo token. Run the requests in order after restarting the server. The valid checkout saves its returned order ID in the collection variable. Additional requests test online method and simulated paid/refunded statuses. This collection is for the local mock runner.

## 8. Run the automated tests

Leave the server running if you want; automated tests create their own separate mock databases. Open a second terminal in the same folder and run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover totals, stock, validation, ownership, saved prices, rollback after a simulated storage failure and two concurrent checkouts competing for the same stock. No AWS account or running MySQL server is used.

Look in `VALIDATION.md` for the actual result obtained when this package was prepared. These are mock tests, not proof of working MySQL transactions, real authentication or deployed persistence.

Check the running server terminal after manual POST requests. Successful orders log `order_created`; rejected orders log `checkout_rejected`. The module avoids logging tokens or database exception text.

## 9. Put your work in the shared GitHub project

If you already cloned Maryam's repository, open that folder and skip cloning. Otherwise replace the placeholder below with the repository URL Maryam gives you:

```powershell
git clone <MARYAM_REPO_URL>
cd CloudCart
git switch main
git pull --ff-only
git switch -c feature/orders-checkout
```

If your feature branch already exists, switch to it with `git switch feature/orders-checkout` instead of creating it again. Commit your existing work before switching branches; do not discard local changes.

Copy **your eight `backend/app/` Python files**, `tests/test_orders.py`, the `postman/` collection, `requirements-lama.txt`, `README_LAMA.md`, `DATABASE_HANDOFF.md`, `PAYMENTS_LAMA.md` and `VALIDATION.md` into matching paths in the shared repository. Add package `__init__.py` files only if missing. Do not replace Maryam's `main.py`, Rawan's `database.py`/`models.py` or existing README/config files. Add your ignore entries and pytest configuration to existing project settings if needed.

Maryam can merge the dependency pins with the shared requirements after checking compatibility; do not overwrite everyone's requirements file.

Run your tests from the shared repository root. If its pytest configuration does not add the root to the Python path, use `python -m pytest` from that root as shown above.

Check the staged files and then commit:

```powershell
git add backend/app/orders.py backend/app/order_schemas.py backend/app/order_service.py backend/app/order_repository.py backend/app/mock_order_repository.py backend/app/order_dependencies.py backend/app/demo_main.py backend/app/mock_payments.py tests/test_orders.py postman/Lama_Orders.postman_collection.json requirements-lama.txt README_LAMA.md DATABASE_HANDOFF.md PAYMENTS_LAMA.md VALIDATION.md
git diff --cached --stat
git commit -m "Add order endpoints and checkout tests with mock database"
git push -u origin feature/orders-checkout
```

If you added missing package files or configuration, stage those specific files too. On GitHub, open a pull request from `feature/orders-checkout` to `main` for Maryam/Rawan to review. This package has not been pushed to your GitHub account.

## 10. Connect the real database later

Share `DATABASE_HANDOFF.md` with Rawan and Maryam early. It defines the seven methods required by your order module. Basmala must use the same products table and the same `stock_quantity` field; your mock products are only local samples.

Remaining integration:

1. Rawan implements a real adapter using her chosen connection/session layer and the agreed schema.
2. Maryam configures that adapter as `app.state.order_repository` in the real application.
3. Maryam connects `get_current_user_id` to her verified login user.
4. Maryam registers your router once with prefix `/api/orders` in her `main.py`.
5. Together you retest against MySQL: persisted orders after restart, valid user foreign keys, real rollback and simultaneous stock purchases.

The database adapter and authentication wiring are still pending. We cannot guarantee that only a connection string will change without seeing Rawan's actual database code. With the agreed interface, your endpoints and checkout service can remain unchanged.

بالمصري: اللي فاضل بعد شغلك المحلي هو توصيل وظائف Rawan واليوزر الحقيقي من Maryam، واختبارهم مع MySQL. مش لازم تعيدي كتابة الأوردرات، بس مش مجرد نحط باسورد الداتابيز وخلاص.

## What to submit for your part

- Successful POST order screenshot showing 201 and total.
- GET list and GET one order screenshots showing 200.
- Invalid stock and invalid quantity screenshots showing 400 and 422.
- Tests showing all passed.
- Terminal logs for successful and rejected checkout.
- Your branch/pull request containing the module, tests and Postman collection.

Label this evidence **local mock checkout**. Save real database/deployment proof after integration.

## Official references

- FastAPI dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Dependency overrides: https://fastapi.tiangolo.com/advanced/testing-dependencies/
- MySQL locking reads: https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html
