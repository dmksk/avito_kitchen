import os
from decimal import Decimal
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="Pizza House Integration Service",
    version="1.0.0",
)

MAIN_SERVICE_URL = os.getenv(
    "MAIN_SERVICE_URL",
    "http://127.0.0.1:8000",
)


MENU = {
    "pizza-margherita": {
        "external_id": "pizza-margherita",
        "name": "Маргарита",
        "price": Decimal("599.00"),
        "stock": 20,
        "is_available": True,
    },
    "pizza-pepperoni": {
        "external_id": "pizza-pepperoni",
        "name": "Пепперони",
        "price": Decimal("699.00"),
        "stock": 15,
        "is_available": True,
    },
    "cola-05": {
        "external_id": "cola-05",
        "name": "Кола 0.5",
        "price": Decimal("149.00"),
        "stock": 30,
        "is_available": True,
    },
}


class ValidationItem(BaseModel):
    external_id: str
    quantity: int = Field(gt=0)
    expected_price: Decimal = Field(gt=0)


class OrderValidationRequest(BaseModel):
    items: list[ValidationItem] = Field(min_length=1)


class StockUpdate(BaseModel):
    stock: int = Field(ge=0)


OrderStatus = Literal[
    "accepted",
    "preparing",
    "ready",
    "in_delivery",
    "delivered",
    "rejected",
]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason: str | None = Field(default=None, max_length=500)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "pizza-house",
    }


@app.get("/menu")
def get_menu():
    return list(MENU.values())


@app.post("/integration/orders/validate")
def validate_order(data: OrderValidationRequest):
    conflicts = []

    for requested_item in data.items:
        menu_item = MENU.get(requested_item.external_id)

        if menu_item is None:
            conflicts.append({
                "type": "product_not_found",
                "external_id": requested_item.external_id,
            })
            continue

        if not menu_item["is_available"]:
            conflicts.append({
                "type": "product_unavailable",
                "external_id": requested_item.external_id,
            })
            continue

        if menu_item["stock"] < requested_item.quantity:
            conflicts.append({
                "type": "insufficient_stock",
                "external_id": requested_item.external_id,
                "requested_quantity": requested_item.quantity,
                "available_quantity": menu_item["stock"],
            })

        if menu_item["price"] != requested_item.expected_price:
            conflicts.append({
                "type": "price_changed",
                "external_id": requested_item.external_id,
                "old_price": str(requested_item.expected_price),
                "new_price": str(menu_item["price"]),
            })

    return {
        "accepted": len(conflicts) == 0,
        "conflicts": conflicts,
    }


@app.patch("/menu/{external_id}/stock")
def update_stock(
    external_id: str,
    data: StockUpdate,
):
    menu_item = MENU.get(external_id)

    if menu_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    menu_item["stock"] = data.stock
    menu_item["is_available"] = data.stock > 0

    return menu_item


@app.patch("/orders/{order_id}/status")
def send_order_status(
    order_id: int,
    data: OrderStatusUpdate,
):
    try:
        response = httpx.patch(
            f"{MAIN_SERVICE_URL}/orders/{order_id}/status",
            json=data.model_dump(),
            timeout=5,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Main service is unavailable",
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json(),
        )

    return response.json()