from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Establishment, Product
from app.schemas import ProductCreate


class EstablishmentNotFoundError(Exception):
    pass


class ProductAlreadyExistsError(Exception):
    pass


def get_establishment_or_raise(
    db: Session,
    establishment_id: int,
) -> Establishment:
    establishment = db.get(Establishment, establishment_id)

    if establishment is None:
        raise EstablishmentNotFoundError

    return establishment


def create_product(
    db: Session,
    establishment_id: int,
    data: ProductCreate,
) -> Product:
    get_establishment_or_raise(db, establishment_id)

    product_data = data.model_dump()
    product = Product(
        establishment_id=establishment_id,
        **product_data,
    )

    db.add(product)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ProductAlreadyExistsError from error

    db.refresh(product)
    return product


def get_products(
    db: Session,
    establishment_id: int,
    only_available: bool = True,
) -> list[Product]:
    get_establishment_or_raise(db, establishment_id)

    statement = (
        select(Product)
        .where(Product.establishment_id == establishment_id)
        .order_by(Product.id)
    )

    if only_available:
        statement = statement.where(Product.is_available.is_(True))

    result = db.scalars(statement)
    return list(result.all())