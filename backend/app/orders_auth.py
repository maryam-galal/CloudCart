"""Authenticate real order requests with the shared login JWT and users table."""
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import JWT_ALGORITHM, JWT_SECRET_KEY
from .database import get_db
from .models import User
from .order_dependencies import bearer


def get_authenticated_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> int:
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    if not JWT_SECRET_KEY:
        raise HTTPException(503, "Authentication is not configured")

    try:
        claims = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        subject = claims["sub"]
        if (
            not isinstance(subject, str)
            or not subject.isascii()
            or not subject.isdecimal()
            or len(subject) > 20
        ):
            raise unauthorized
        user_id = int(subject)
        if not 0 < user_id <= 18446744073709551615:
            raise unauthorized
    except (jwt.InvalidTokenError, ValueError, TypeError) as error:
        raise unauthorized from error

    if db.get(User, user_id) is None:
        raise unauthorized
    return user_id
