"""Run isolated order/auth checks without using or changing real DB credentials."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    # create_engine builds a MySQL engine but does not connect. The integration
    # fixture replaces every database dependency with its temporary SQLite DB.
    environment["DATABASE_URL"] = (
        "mysql+pymysql://test:test@127.0.0.1/cloudcart_integration_test"
    )
    environment["JWT_SECRET_KEY"] = (
        "isolated-tests-only-secret-with-at-least-32-characters"
    )
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(root / "backend"), str(root)]
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_orders.py",
         "tests/test_orders_integration.py", "tests/test_security.py", "-q"],
        cwd=root,
        env=environment,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
