
from fastapi import FastAPI
from app.auth import router as auth_router
from app.products import router as products_router

app = FastAPI(
    title="CloudCart API",
    description="Backend API for the CloudCart application",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(products_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "application": "CloudCart API",
    }
