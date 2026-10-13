
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hashing():
    password = "ExamplePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword123!", hashed)


def test_token_creation_and_decoding():
    token = create_access_token("user-123")
    claims = decode_access_token(token)

    assert claims["sub"] == "user-123"
    assert "exp" in claims