"""rename adress to address

Revision ID: d78665a69b5e
Revises: 7f1c0dc104d2
Create Date: 2026-08-27 21:28:36.513126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd78665a69b5e'
down_revision: Union[str, Sequence[str], None] = '7f1c0dc104d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "establishments",
        "adress",
        new_column_name="address",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "establishments",
        "address",
        new_column_name="adress",
    )
