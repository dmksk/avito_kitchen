import os

import httpx

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Establishment, Order, OrderItem, Product
from app.schemas import OrderCreate, OrderStatusUpdate


DELIVERY_PRICE = Decimal("199.00")
ESTABLISHMENT_SERVICE_URL = os.getenv(
    "ESTABLISHMENT_SERVICE_URL",
    "http://127.0.0.1:8001",
)

class OrderEstablishmentNotFoundError(Exception):
    pass


class OrderNotFoundError(Exception):
    pass


class OrderConflictError(Exception):
    def __init__(self, conflicts: list[dict]):
        self.conflicts = conflicts
        super().__init__("Order contains conflicting items")


class InvalidOrderStatusTransitionError(Exception):
    pass

class EstablishmentServiceUnavailableError(Exception):
    pass

ALLOWED_STATUS_TRANSITIONS = {
    "pending": {"accepted", "rejected", "cancelled"},
    "accepted": {"preparing", "rejected", "cancelled"},
    "preparing": {"ready", "rejected"},
    "ready": {"in_delivery"},
    "in_delivery": {"delivered"},
    "delivered": set(),
    "rejected": set(),
    "cancelled": set(),
}


def get_order_or_raise(
    db: Session,
    order_id: int,
) -> Order:
    order = db.get(Order, order_id)

    if order is None:
        raise OrderNotFoundError

    return order

def validate_with_establishment(
    products_by_id: dict[int, Product],
    data: OrderCreate,
) -> None:
    request_data = {
        "items": [
            {
                "external_id": products_by_id[item.product_id].external_id,
                "quantity": item.quantity,
                "expected_price": str(
                    products_by_id[item.product_id].price
                ),
            }
            for item in data.items
        ]
    }

    try:
        response = httpx.post(
            (
                f"{ESTABLISHMENT_SERVICE_URL}"
                "/integration/orders/validate"
            ),
            json=request_data,
            timeout=5,
        )
    except httpx.RequestError as error:
        raise EstablishmentServiceUnavailableError from error

    if response.status_code != 200:
        raise EstablishmentServiceUnavailableError

    result = response.json()

    if not result["accepted"]:
        raise OrderConflictError(result["conflicts"])

def create_order(
    db: Session,
    establishment_id: int,
    data: OrderCreate,
) -> Order:
    establishment = db.get(Establishment, establishment_id)

    if establishment is None:
        raise OrderEstablishmentNotFoundError

    if not establishment.is_active:
        raise OrderConflictError([
            {
                "type": "establishment_inactive",
                "establishment_id": establishment_id,
            }
        ])

    product_ids = [item.product_id for item in data.items]

    products = db.scalars(
        select(Product).where(
            Product.establishment_id == establishment_id,
            Product.id.in_(product_ids),
        )
    ).all()

    products_by_id = {
        product.id: product
        for product in products
    }

    conflicts = []
    processed_product_ids = set()

    for item in data.items:
        if item.product_id in processed_product_ids:
            conflicts.append({
                "type": "duplicate_product",
                "product_id": item.product_id,
            })
            continue

        processed_product_ids.add(item.product_id)
        product = products_by_id.get(item.product_id)

        if product is None:
            conflicts.append({
                "type": "product_not_found",
                "product_id": item.product_id,
            })
            continue

        if not product.is_available:
            conflicts.append({
                "type": "product_unavailable",
                "product_id": product.id,
                "product_name": product.name,
            })
            continue

        if product.price != item.expected_price:
            conflicts.append({
                "type": "price_changed",
                "product_id": product.id,
                "product_name": product.name,
                "old_price": str(item.expected_price),
                "new_price": str(product.price),
            })

    if conflicts:
        raise OrderConflictError(conflicts)

    validate_with_establishment(products_by_id, data)

    order = Order(
        establishment_id=establishment_id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        delivery_address=data.delivery_address,
        status="pending",
        items_total=Decimal("0.00"),
        delivery_price=DELIVERY_PRICE,
        total_price=Decimal("0.00"),
    )

    items_total = Decimal("0.00")

    for item in data.items:
        product = products_by_id[item.product_id]
        line_total = product.price * item.quantity
        items_total += line_total

        order.items.append(
            OrderItem(
                product_id=product.id,
                external_product_id=product.external_id,
                product_name=product.name,
                unit_price=product.price,
                quantity=item.quantity,
                line_total=line_total,
            )
        )

    order.items_total = items_total
    order.total_price = items_total + DELIVERY_PRICE

    db.add(order)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order


def get_order(
    db: Session,
    order_id: int,
) -> Order:
    return get_order_or_raise(db, order_id)


def get_orders(
    db: Session,
    establishment_id: int | None = None,
) -> list[Order]:
    statement = select(Order).order_by(Order.id.desc())

    if establishment_id is not None:
        statement = statement.where(
            Order.establishment_id == establishment_id
        )

    result = db.scalars(statement)
    return list(result.all())


def update_order_status(
    db: Session,
    order_id: int,
    data: OrderStatusUpdate,
) -> Order:
    order = get_order_or_raise(db, order_id)

    allowed_statuses = ALLOWED_STATUS_TRANSITIONS[order.status]

    if data.status not in allowed_statuses:
        raise InvalidOrderStatusTransitionError(
            f"Cannot change status from "
            f"'{order.status}' to '{data.status}'"
        )

    if data.status == "rejected" and not data.reason:
        raise InvalidOrderStatusTransitionError(
            "Rejection reason is required"
        )

    order.status = data.status

    if data.status == "rejected":
        order.rejection_reason = data.reason
    else:
        order.rejection_reason = None

    db.commit()
    db.refresh(order)

    return order