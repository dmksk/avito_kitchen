from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy.orm import Session

app = FastAPI()

from app.schemas import OrderCalculateRequest, EstablishmentCreate, EstablishmentResponse, ProductCreate, ProductResponse, OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.pricing import calculate_order_total
from app.services.establishments import EstablismentAlreadyExistError
from app.database import get_db
from app.services.establishments import create_establishment, get_establishments
from app.services.products import EstablishmentNotFoundError, ProductAlreadyExistsError, create_product, get_products
from app.services.orders import (
    EstablishmentServiceUnavailableError,
    InvalidOrderStatusTransitionError,
    OrderConflictError,
    OrderEstablishmentNotFoundError,
    OrderNotFoundError,
    create_order as create_order_service,
    get_order as get_order_service,
    get_orders as get_orders_service,
    update_order_status as update_order_status_service,
)
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "avito-kitchen"
    }
@app.post("/orders/calculate")
def calculate_order(request: OrderCalculateRequest):
    items = []
    for item in request.items:
        item_data = {
        "name": item.name,
        "price": item.price,
        "quantity": item.quantity
        }
        items.append(item_data)
    return calculate_order_total(items, request.delivery_price, request.discount)
@app.post("/establishments", response_model= EstablishmentResponse, status_code= status.HTTP_201_CREATED)
def create_establishments_endpoint(data: EstablishmentCreate,
                                   db: Session = Depends(get_db)):
    try:
        return create_establishment(db, data)
    except EstablismentAlreadyExistError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Establishment with this external_id already exists",
        )from error

@app.get("/establishments", response_model=list[EstablishmentResponse])
def get_establishments_endpoint(db: Session = Depends(get_db)):
    return get_establishments(db)

@app.post(
    "/establishments/{establishment_id}/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Establishment not found"},
        409: {"description": "Product already exists"},
    },
)
def create_product_endpoint(
    establishment_id: int,
    data: ProductCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_product(db, establishment_id, data)
    except EstablishmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Establishment not found",
        ) from error
    except ProductAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Product with this external_id already exists "
                "in this establishment"
            ),
        ) from error


@app.get(
    "/establishments/{establishment_id}/products",
    response_model=list[ProductResponse],
    responses={
        404: {"description": "Establishment not found"},
    },
)
def get_products_endpoint(
    establishment_id: int,
    only_available: bool = True,
    db: Session = Depends(get_db),
):
    try:
        return get_products(
            db,
            establishment_id,
            only_available=only_available,
        )
    except EstablishmentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Establishment not found",
        ) from error

@app.post(
    "/establishments/{establishment_id}/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order_endpoint(
    establishment_id: int,
    data: OrderCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_order_service(db, establishment_id, data)
    except OrderEstablishmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Establishment not found",
        )
    except OrderConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Order cannot be created",
                "conflicts": error.conflicts,
            },
        )
    except EstablishmentServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Establishment service is unavailable",
        )

@app.get(
    "/orders",
    response_model=list[OrderResponse],
)
def get_orders_endpoint(
    establishment_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_orders_service(db, establishment_id)


@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
)
def get_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_order_service(db, order_id)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )


@app.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
)
def update_order_status_endpoint(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_order_status_service(db, order_id, data)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    except InvalidOrderStatusTransitionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )