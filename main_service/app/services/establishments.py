from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Establishment
from app.schemas import EstablishmentCreate
from sqlalchemy.exc import IntegrityError

class EstablismentAlreadyExistError(Exception):
    pass
def create_establishment(
        db: Session,
        data: EstablishmentCreate
) -> Establishment:
    establishment_data = data.model_dump()
    establishment = Establishment(**establishment_data)
    db.add(establishment)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise EstablismentAlreadyExistError from error
    db.refresh(establishment)
    return establishment

def get_establishments(db: Session) -> list[Establishment]:
    statement = select(Establishment).order_by(Establishment.id)
    result = db.scalars(statement)
    return list(result.all())