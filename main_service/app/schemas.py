from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Literal

class OrderItem(BaseModel):
    name: str = Field(min_length = 1)
    price: float = Field(gt = 0)
    quantity: int = Field(gt = 0)

class OrderCalculateRequest(BaseModel):
    items: list[OrderItem] = Field(min_length = 1)
    delivery_price: float = Field(ge = 0)
    discount: float= Field(ge = 0)

class EstablishmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    external_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    establishment_type: str = Field(min_length=1, max_length=30)
    address: str = Field(min_length=1, max_length=500)

class EstablishmentResponse(EstablishmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool

class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    external_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt = 0, max_digits=12, decimal_places=2)
    is_available: bool = True

class ProductResponse(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    establishment_id: int

class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    expected_price: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    customer_name: str = Field(min_length=1, max_length=100)
    customer_phone: str = Field(min_length=5, max_length=30)
    delivery_address: str = Field(min_length=5, max_length=500)
    items: list[OrderItemCreate] = Field(min_length=1)

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    external_product_id: str
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal

class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    establishment_id: int
    customer_name: str
    customer_phone: str
    delivery_address: str
    status: str
    rejection_reason: str | None
    items_total: Decimal
    delivery_price: Decimal
    total_price: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]

OrderStatus = Literal[
    "pending",
    "accepted",
    "preparing",
    "ready",
    "in_delivery",
    "delivered",
    "rejected",
    "cancelled",
]

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason: str | None = Field(default=None, max_length=500)