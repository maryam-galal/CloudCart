
from fastapi import FastAPI
from app.auth import router as auth_router
from app.database import SessionLocal
from app.database_orders import SQLAlchemyOrderRepository
from app.order_dependencies import get_current_user_id
from app.orders import router as orders_router
from app.orders_auth import get_authenticated_user_id

app = FastAPI(
    title="CloudCart API",
    description="Backend API for the CloudCart application",
    version="1.0.0",
)

app.include_router(auth_router)
app.state.order_repository = SQLAlchemyOrderRepository(SessionLocal)
app.dependency_overrides[get_current_user_id] = get_authenticated_user_id
app.include_router(orders_router, prefix="/api/orders")


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "application": "CloudCart API",
    }
