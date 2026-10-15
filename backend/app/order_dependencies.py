"""Two integration points: Rawan's repository and Maryam's authentication."""
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .order_repository import OrderRepository

bearer = HTTPBearer(auto_error=False)


def get_order_repository(request: Request) -> OrderRepository:
    repository = getattr(request.app.state, "order_repository", None)
    if repository is None:
        raise HTTPException(503, "Order database is not configured")
    return repository


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> int:
    # Maryam replaces/wires this dependency to her verified authenticated user.
    # Do not accept user_id from the request body.
    raise HTTPException(401, "Authentication is not configured",
                        headers={"WWW-Authenticate": "Bearer"})
