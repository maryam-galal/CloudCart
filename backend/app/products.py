
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Path, Response, status
from pydantic import BaseModel, ConfigDict, Field


router = APIRouter(prefix="/api/products", tags=["Products"])


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)
    image_key: str | None = Field(default=None, max_length=255)


class ProductUpdate(ProductCreate):
    pass


class ProductResponse(ProductCreate):
    product_id: int


# Temporary sample data; replace with Rawan's database layer later.
_products: dict[int, dict] = {
    1: {
        "product_id": 1,
        "name": "Wireless Mouse",
        "description": "Sample product for API testing",
        "price": Decimal("25.99"),
        "stock_quantity": 50,
        "image_key": None,
    },
    2: {
        "product_id": 2,
        "name": "USB-C Cable",
        "description": "Sample USB-C charging cable",
        "price": Decimal("9.50"),
        "stock_quantity": 100,
        "image_key": None,
    },
}

_next_id = 3


@router.get("", response_model=list[ProductResponse])
def get_products():
    return list(_products.values())


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int = Path(gt=0)):
    product = _products.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(product_data: ProductCreate):
    global _next_id

    product = product_data.model_dump()
    product["product_id"] = _next_id
    _products[_next_id] = product
    _next_id += 1

    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
):
    if product_id not in _products:
        raise HTTPException(status_code=404, detail="Product not found")

    updated_product = product_data.model_dump()
    updated_product["product_id"] = product_id
    _products[product_id] = updated_product

    return updated_product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int):
    if product_id not in _products:
        raise HTTPException(status_code=404, detail="Product not found")

    del _products[product_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
