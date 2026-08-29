from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import String, true, ForeignKey, Numeric, UniqueConstraint, func, CheckConstraint, DateTime
from decimal import Decimal
from datetime import datetime

class Establishment(Base):
    __tablename__ = "establishments"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    establishment_type: Mapped[str] = mapped_column(String(30))
    address: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(100))
    establishment_id: Mapped[int] = mapped_column(ForeignKey("establishments.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None ] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    is_available: Mapped[bool] = mapped_column(default=True, server_default=true())
    __table_args__ = (
        UniqueConstraint(
            "establishment_id",
            "external_id",
            name="uq_products_establishment_external_id",
        ),
    )

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    establishment_id: Mapped[int] = mapped_column(
        ForeignKey("establishments.id", ondelete="RESTRICT"),
        index=True,
    )

    customer_name: Mapped[str] = mapped_column(String(100))
    customer_phone: Mapped[str] = mapped_column(String(30))
    delivery_address: Mapped[str] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        server_default="pending",
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    items_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_order_items_quantity_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
    )

    external_product_id: Mapped[str] = mapped_column(String(100))
    product_name: Mapped[str] = mapped_column(String(200))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column()
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped["Order"] = relationship(back_populates="items")