"""Lama's standalone LOCAL runner. Keep Maryam's main.py separate."""
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from .mock_order_repository import MockOrderRepository
from .mock_payments import router as mock_payments_router
from .order_dependencies import bearer, get_current_user_id
from .orders import router

def get_demo_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> int:
    demo_users = {"mock-user-1": 1, "mock-user-2": 2}
    if credentials is None or credentials.credentials not in demo_users:
        raise HTTPException(401, "Use a local demo token",
                            headers={"WWW-Authenticate": "Bearer"})
    return demo_users[credentials.credentials]


def create_demo_app(repository=None):
    application = FastAPI(title="CloudCart — Lama's local orders demo")
    application.state.order_repository = (
        repository if repository is not None else MockOrderRepository()
    )
    application.dependency_overrides[get_current_user_id] = get_demo_user_id
    application.include_router(router, prefix="/api/orders")
    application.include_router(mock_payments_router, prefix="/mock")

    @application.get("/health")
    def health():
        return {"status": "ok", "mode": "local-mock"}

    return application


logging.basicConfig(level=logging.INFO)
app = create_demo_app()
