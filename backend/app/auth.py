
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


@router.post("/signup", status_code=201)
def signup(request: SignupRequest):
    # Temporary scaffold; database persistence comes next.
    return {
        "message": "Signup endpoint scaffold is ready",
        "email": request.email,
    }


@router.post("/login")
def login(request: LoginRequest):
    # Password verification and token generation come next.
    return {
        "message": "Login endpoint scaffold is ready",
        "email": request.email,
    }